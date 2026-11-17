from decimal import Decimal
from typing import Iterable, Optional

from django.db.models import (
    Avg,
    Case,
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    FloatField,
    IntegerField,
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
    ProductComposition.objects.filter(product=OuterRef("pk"))
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
    ProductReview.objects.filter(product=OuterRef("pk"))
    .values("product")
    .annotate(avg=Avg("rating"))
    .values("avg")[:1]
)

_reviews_cnt_sq = (
    ProductReview.objects.filter(product=OuterRef("pk"))
    .values("product")
    .annotate(cnt=Count("id"))
    .values("cnt")[:1]
)


def get_admin_product_list_queryset() -> QuerySet[Product]:
    """
    Optimized queryset tailored for Admin Product List.
    - Joins category, sub_category, and brand via select_related.
    - Prefetches variants and their option values in bulk with option names.
    - Annotates reviews_count_annotated and average_rating via scalar subqueries.
    - Annotates computed_final_price for instant sorting and final_price retrieval.
    - Defers unused heavy text fields (description, meta_title, meta_description).
    """
    return (
        Product.objects.select_related("category", "sub_category", "brand")
        .prefetch_related(
            Prefetch(
                "variants",
                queryset=ProductVariant.objects.only(
                    "id", "product_id", "price", "stock", "image"
                ).prefetch_related(
                    Prefetch(
                        "option_values",
                        queryset=ProductOptionValue.objects.select_related("option").only(
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


def prefetch_active_offers_for_products(products: Iterable[Product]) -> None:
    """
    Batch-evaluates and caches active offers for an iterable of Product instances
    and their prefetched variants in a single database query.
    """
    products_list = list(products)
    if not products_list:
        return

    now = timezone.now()
    active_offers = list(
        Offer.objects.filter(is_active=True, start_date__lte=now, end_date__gte=now)
        .prefetch_related("products", "categories", "sub_categories")
        .order_by("-discount_value")
    )

    if not active_offers:
        for product in products_list:
            product._cached_active_offer = None
            if hasattr(product, "_prefetched_objects_cache"):
                variants = product._prefetched_objects_cache.get("variants")
                if variants:
                    for variant in variants:
                        variant._cached_active_offer = None
                        variant._cached_product = product
        return

    offer_rules = []
    for offer in active_offers:
        offer_rules.append(
            (
                offer,
                set(p.id for p in offer.products.all()),
                set(c.id for c in offer.categories.all()),
                set(sc.id for sc in offer.sub_categories.all()),
            )
        )

    for product in products_list:
        matched_offer = None
        for offer, p_ids, c_ids, sc_ids in offer_rules:
            if (
                product.id in p_ids
                or (product.category_id and product.category_id in c_ids)
                or (product.sub_category_id and product.sub_category_id in sc_ids)
            ):
                matched_offer = offer
                break

        product._cached_active_offer = matched_offer

        if hasattr(product, "_prefetched_objects_cache"):
            variants = product._prefetched_objects_cache.get("variants")
            if variants:
                for variant in variants:
                    variant._cached_active_offer = matched_offer
                    variant._cached_product = product
