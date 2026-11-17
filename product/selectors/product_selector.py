from typing import Any, Iterable

from django.core.cache import cache
from django.db.models import (
    Avg,
    Case,
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    FloatField,
    IntegerField,
    Max,
    OuterRef,
    Prefetch,
    QuerySet,
    Subquery,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce
from django.utils import timezone

from product.models import (
    Offer,
    Product,
    ProductComposition,
    ProductOptionValue,
    ProductReview,
    ProductVariant,
)

_dynamic_price_sq = (
    ProductComposition.objects
    .filter(product=OuterRef("pk"))
    .values("product")
    .annotate(
        total=Sum(
            ExpressionWrapper(
                F("metric__price_per_unit") * F("quantity"),
                output_field=DecimalField(max_digits=100, decimal_places=2),
            )
        )
    )
    .values("total")[:1]
)

FINAL_PRICE_ANNOTATION = Case(
    When(
        use_dynamic_pricing=True,
        then=Coalesce(
            Subquery(
                _dynamic_price_sq,
                output_field=DecimalField(max_digits=100, decimal_places=2),
            ),
            Value(0, output_field=DecimalField(max_digits=100, decimal_places=2)),
        )
        + Coalesce(
            F("base_making_charge"),
            Value(0, output_field=DecimalField(max_digits=100, decimal_places=2)),
        ),
    ),
    default=F("price"),
    output_field=DecimalField(max_digits=100, decimal_places=2),
)

_reviews_avg_sq = (
    ProductReview.objects
    .filter(product=OuterRef("pk"))
    .values("product")
    .annotate(avg=Avg("rating"))
    .values("avg")[:1]
)

_reviews_cnt_sq = (
    ProductReview.objects
    .filter(product=OuterRef("pk"))
    .values("product")
    .annotate(cnt=Count("id"))
    .values("cnt")[:1]
)


def get_admin_product_list_queryset() -> QuerySet[Product]:
    """
    Optimized queryset tailored for Admin and Store Product Lists.
    - Joins category, sub_category, and brand via select_related.
    - Prefetches variants and their option values in bulk with option names.
    - Annotates reviews_count_annotated and average_rating via scalar subqueries.
    - Annotates computed_final_price for instant sorting and final_price retrieval.
    - Defers unused heavy text fields (description, meta_title, meta_description).
    """
    return (
        Product.objects
        .select_related("category", "sub_category", "brand")
        .prefetch_related(
            Prefetch(
                "variants",
                queryset=ProductVariant.objects.only(
                    "id", "product_id", "price", "stock", "image"
                ).prefetch_related(
                    Prefetch(
                        "option_values",
                        queryset=ProductOptionValue.objects.select_related(
                            "option"
                        ).only(
                            "id", "value", "option_id", "option__id", "option__name"
                        ),
                    )
                ),
            )
        )
        .annotate(
            average_rating=Coalesce(
                Subquery(_reviews_avg_sq, output_field=FloatField()),
                Value(0.0, output_field=FloatField()),
            ),
            reviews_count_annotated=Coalesce(
                Subquery(_reviews_cnt_sq, output_field=IntegerField()),
                Value(0, output_field=IntegerField()),
            ),
            computed_final_price=FINAL_PRICE_ANNOTATION,
        )
        .defer("description", "meta_title", "meta_description")
        .order_by("-created_at")
    )


def get_standalone_product_list_queryset() -> QuerySet[Product]:
    """
    Optimized queryset for products that have no variants (standalone products).
    Used in variant mode.
    """
    return (
        Product.objects
        .filter(variants__isnull=True)
        .select_related("category", "sub_category", "brand")
        .annotate(
            average_rating=Coalesce(
                Subquery(_reviews_avg_sq, output_field=FloatField()),
                Value(0.0, output_field=FloatField()),
            ),
            reviews_count_annotated=Coalesce(
                Subquery(_reviews_cnt_sq, output_field=IntegerField()),
                Value(0, output_field=IntegerField()),
            ),
            computed_final_price=FINAL_PRICE_ANNOTATION,
        )
        .defer("description", "meta_title", "meta_description")
        .order_by("-created_at")
    )


def get_product_variant_list_queryset() -> QuerySet[ProductVariant]:
    """
    Optimized queryset for product variants listing.
    Prefetches product relations, option values, and sibling variants with zero N+1 queries.
    """
    return (
        ProductVariant.objects
        .select_related(
            "product",
            "product__category",
            "product__sub_category",
            "product__brand",
        )
        .prefetch_related(
            Prefetch(
                "option_values",
                queryset=ProductOptionValue.objects.select_related("option").only(
                    "id", "value", "option_id", "option__id", "option__name"
                ),
            ),
            Prefetch(
                "product__variants",
                queryset=ProductVariant.objects.only(
                    "id", "product_id", "price", "stock", "image"
                ).prefetch_related(
                    Prefetch(
                        "option_values",
                        queryset=ProductOptionValue.objects.select_related(
                            "option"
                        ).only(
                            "id", "value", "option_id", "option__id", "option__name"
                        ),
                    )
                ),
            ),
        )
        .only(
            "id",
            "product_id",
            "price",
            "stock",
            "image",
            "created_at",
            "updated_at",
            "product__id",
            "product__name",
            "product__slug",
            "product__barcode",
            "product__price",
            "product__market_price",
            "product__thumbnail_image",
            "product__thumbnail_alt_description",
            "product__is_popular",
            "product__is_featured",
            "product__require_custom_image",
            "product__fast_shipping",
            "product__warranty",
            "product__use_dynamic_pricing",
            "product__base_making_charge",
            "product__created_at",
            "product__updated_at",
            "product__category_id",
            "product__sub_category_id",
            "product__brand_id",
            "product__category__id",
            "product__category__name",
            "product__category__slug",
            "product__sub_category__id",
            "product__sub_category__name",
            "product__sub_category__slug",
            "product__sub_category__description",
            "product__sub_category__image",
            "product__brand__id",
            "product__brand__name",
            "product__brand__slug",
            "product__brand__image",
        )
        .order_by("-created_at")
    )


def get_global_max_price(is_variant_mode: bool = False) -> float:
    """
    Cached computation of global max_price across all products/variants.
    Prevents running heavy full-table aggregate calculations on every request.
    """
    cache_key = f"store_global_max_price_variant_{is_variant_mode}"
    cached_val = cache.get(cache_key)
    if cached_val is not None:
        return cached_val

    if not is_variant_mode:
        val = float(
            Product.objects.annotate(
                computed_final_price=FINAL_PRICE_ANNOTATION
            ).aggregate(m=Max("computed_final_price"))["m"]
            or 0.0
        )
    else:
        variant_max = float(
            ProductVariant.objects.aggregate(m=Max("price"))["m"] or 0.0
        )
        standalone_product_max = float(
            Product.objects
            .filter(variants__isnull=True)
            .annotate(computed_final_price=FINAL_PRICE_ANNOTATION)
            .aggregate(m=Max("computed_final_price"))["m"]
            or 0.0
        )
        fallback_max = float(
            Product.objects.filter(
                variants__isnull=False,
                variants__price__isnull=True,
            ).aggregate(m=Max("price"))["m"]
            or 0.0
        )
        val = max(variant_max, standalone_product_max, fallback_max)

    cache.set(cache_key, val, timeout=300)
    return val


def prefetch_active_offers_and_reviews_for_items(items: Iterable[Any]) -> None:
    """
    Batch-evaluates and caches active offers and review aggregates for an iterable
    of mixed Product and ProductVariant items in 2 fast queries total.
    """
    items_list = list(items)
    if not items_list:
        return

    # 1. Collect all unique products
    product_map = {}
    for item in items_list:
        if isinstance(item, ProductVariant):
            prod = getattr(item, "_cached_product", None) or item.product
            if prod:
                item._cached_product = prod
                product_map[prod.id] = prod
        elif isinstance(item, Product):
            product_map[item.id] = item

    # 2. Batch-load review aggregates for all products on the page (1 query)
    if product_map:
        reviews_data = (
            ProductReview.objects
            .filter(product_id__in=product_map.keys())
            .values("product_id")
            .annotate(
                avg_rating=Avg("rating"),
                reviews_count=Count("id"),
            )
        )
        reviews_lookup = {
            r["product_id"]: (r["avg_rating"] or 0.0, r["reviews_count"] or 0)
            for r in reviews_data
        }
        for prod_id, prod in product_map.items():
            avg_r, cnt_r = reviews_lookup.get(prod_id, (0.0, 0))
            if not hasattr(prod, "average_rating") or prod.average_rating is None:
                prod.average_rating = avg_r
            if (
                not hasattr(prod, "reviews_count_annotated")
                or prod.reviews_count_annotated is None
            ):
                prod.reviews_count_annotated = cnt_r

    # 3. Batch-load active offers (1 query)
    now = timezone.now()
    active_offers = list(
        Offer.objects
        .filter(is_active=True, start_date__lte=now, end_date__gte=now)
        .prefetch_related("products", "categories", "sub_categories")
        .order_by("-discount_value")
    )

    if not active_offers:
        for item in items_list:
            if isinstance(item, ProductVariant):
                item._cached_active_offer = None
                prod = getattr(item, "_cached_product", None) or item.product
                if prod:
                    prod._cached_active_offer = None
            else:
                item._cached_active_offer = None
        return

    offer_rules = []
    for offer in active_offers:
        offer_rules.append((
            offer,
            set(p.id for p in offer.products.all()),
            set(c.id for c in offer.categories.all()),
            set(sc.id for sc in offer.sub_categories.all()),
        ))

    for item in items_list:
        if isinstance(item, ProductVariant):
            prod = getattr(item, "_cached_product", None) or item.product
            variant = item
        else:
            prod = item
            variant = None

        matched_offer = None
        if prod:
            p_id = prod.id
            c_id = getattr(prod, "category_id", None)
            sc_id = getattr(prod, "sub_category_id", None)
            for offer, p_ids, c_ids, sc_ids in offer_rules:
                if (
                    p_id in p_ids
                    or (c_id and c_id in c_ids)
                    or (sc_id and sc_id in sc_ids)
                ):
                    matched_offer = offer
                    break

            prod._cached_active_offer = matched_offer

            if hasattr(prod, "_prefetched_objects_cache"):
                variants = prod._prefetched_objects_cache.get("variants")
                if variants:
                    for v in variants:
                        v._cached_active_offer = matched_offer
                        v._cached_product = prod

        if variant:
            variant._cached_active_offer = matched_offer
            if prod:
                variant._cached_product = prod


def prefetch_active_offers_for_products(products: Iterable[Product]) -> None:
    """
    Backwards-compatible wrapper that batch-evaluates active offers and reviews.
    """
    prefetch_active_offers_and_reviews_for_items(products)
