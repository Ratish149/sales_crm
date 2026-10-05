from django.db.models import Q
from django.utils import timezone
from django_filters import rest_framework as django_filters

from .models import Brand, Offer, Product, ProductReview, ProductVariant, SubCategory


class BrandFilterSet(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr="icontains")
    slug = django_filters.CharFilter(lookup_expr="iexact")

    class Meta:
        model = Brand
        fields = ["name", "slug"]


class SubCategoryFilterSet(django_filters.FilterSet):
    category = django_filters.CharFilter(
        field_name="category__id", lookup_expr="iexact"
    )
    category_slug = django_filters.CharFilter(
        field_name="category__slug", lookup_expr="iexact"
    )

    class Meta:
        model = SubCategory
        fields = ["category", "category_slug"]


class ProductFilterSet(django_filters.FilterSet):
    category = django_filters.CharFilter(
        field_name="category__slug", lookup_expr="iexact"
    )
    category_id = django_filters.NumberFilter(field_name="category_id")
    sub_category = django_filters.CharFilter(
        field_name="sub_category__slug", lookup_expr="iexact"
    )
    sub_category_id = django_filters.NumberFilter(field_name="sub_category_id")
    brand = django_filters.CharFilter(method="filter_by_brand")
    brand_id = django_filters.NumberFilter(field_name="brand_id")
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")
    is_popular = django_filters.BooleanFilter(field_name="is_popular")
    is_featured = django_filters.BooleanFilter(field_name="is_featured")
    offer = django_filters.CharFilter(method="filter_by_offer")
    barcode = django_filters.CharFilter(field_name="barcode", lookup_expr="exact")
    flash_sales = django_filters.BooleanFilter(method="filter_flash_sales")

    class Meta:
        model = Product
        fields = [
            "category",
            "category_id",
            "sub_category",
            "sub_category_id",
            "brand",
            "brand_id",
            "min_price",
            "max_price",
            "is_popular",
            "is_featured",
            "offer",
            "flash_sales",
            "barcode",
        ]

    def filter_by_brand(self, queryset, name, value):
        if not value:
            return queryset
        if str(value).isdigit():
            return queryset.filter(Q(brand_id=value) | Q(brand__slug__iexact=value))
        return queryset.filter(brand__slug__iexact=value)

    def filter_flash_sales(self, queryset, name, value):
        if not value:
            return queryset

        now = timezone.now()
        active_offers = Offer.objects.filter(
            is_active=True, start_date__lte=now, end_date__gte=now
        )

        if not active_offers.exists():
            return queryset  # no active offers → return all products

        category_ids = list(
            filter(None, active_offers.values_list("categories", flat=True))
        )
        sub_category_ids = list(
            filter(None, active_offers.values_list("sub_categories", flat=True))
        )
        product_ids = list(
            filter(None, active_offers.values_list("products", flat=True))
        )

        q = Q()
        if category_ids:
            q |= Q(category_id__in=category_ids)
        if sub_category_ids:
            q |= Q(sub_category_id__in=sub_category_ids)
        if product_ids:
            q |= Q(id__in=product_ids)

        if not q:
            return queryset  # offers exist but have no rules → return all

        return queryset.filter(q).distinct()

    def filter_by_offer(self, queryset, name, value):
        if not value:
            return queryset
        try:
            offer = Offer.objects.get(slug=value)
        except Offer.DoesNotExist:
            return queryset.none()

        q_objects = Q()
        has_conditions = False

        if offer.products.exists():
            q_objects |= Q(id__in=offer.products.values_list("id", flat=True))
            has_conditions = True

        if offer.categories.exists():
            q_objects |= Q(category__in=offer.categories.all())
            has_conditions = True

        if offer.sub_categories.exists():
            q_objects |= Q(sub_category__in=offer.sub_categories.all())
            has_conditions = True

        if not has_conditions:
            return queryset.none()

        return queryset.filter(q_objects).distinct()


class ProductVariantFilterSet(django_filters.FilterSet):
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")
    category = django_filters.CharFilter(field_name="product__category__slug")
    category_id = django_filters.NumberFilter(field_name="product__category_id")
    sub_category = django_filters.CharFilter(field_name="product__sub_category__slug")
    sub_category_id = django_filters.NumberFilter(field_name="product__sub_category_id")
    brand = django_filters.CharFilter(method="filter_by_brand")
    brand_id = django_filters.NumberFilter(field_name="product__brand_id")
    status = django_filters.ChoiceFilter(
        field_name="product__status", choices=Product.STATUS_CHOICES
    )
    is_popular = django_filters.BooleanFilter(field_name="product__is_popular")
    is_featured = django_filters.BooleanFilter(field_name="product__is_featured")
    offer = django_filters.CharFilter(method="filter_by_offer")
    flash_sales = django_filters.BooleanFilter(method="filter_flash_sales")

    class Meta:
        model = ProductVariant
        fields = [
            "category",
            "category_id",
            "sub_category",
            "sub_category_id",
            "brand",
            "brand_id",
            "min_price",
            "max_price",
            "status",
            "is_popular",
            "is_featured",
            "offer",
            "flash_sales",
        ]

    def filter_by_brand(self, queryset, name, value):
        if not value:
            return queryset
        if str(value).isdigit():
            return queryset.filter(
                Q(product__brand_id=value) | Q(product__brand__slug__iexact=value)
            )
        return queryset.filter(product__brand__slug__iexact=value)

    def filter_flash_sales(self, queryset, name, value):
        if not value:
            return queryset

        now = timezone.now()
        active_offers = Offer.objects.filter(
            is_active=True, start_date__lte=now, end_date__gte=now
        )

        if not active_offers.exists():
            return queryset  # no active offers → return all variants

        category_ids = list(
            filter(None, active_offers.values_list("categories", flat=True))
        )
        sub_category_ids = list(
            filter(None, active_offers.values_list("sub_categories", flat=True))
        )
        product_ids = list(
            filter(None, active_offers.values_list("products", flat=True))
        )

        q = Q()
        if category_ids:
            q |= Q(product__category_id__in=category_ids)
        if sub_category_ids:
            q |= Q(product__sub_category_id__in=sub_category_ids)
        if product_ids:
            q |= Q(product_id__in=product_ids)

        if not q:
            return queryset

        return queryset.filter(q).distinct()

    def filter_by_offer(self, queryset, name, value):
        if not value:
            return queryset
        try:
            offer = Offer.objects.get(slug=value)
        except Offer.DoesNotExist:
            return queryset.none()

        q_objects = Q()
        has_conditions = False

        if offer.products.exists():
            q_objects |= Q(product_id__in=offer.products.values_list("id", flat=True))
            has_conditions = True

        if offer.categories.exists():
            q_objects |= Q(product__category__in=offer.categories.all())
            has_conditions = True

        if offer.sub_categories.exists():
            q_objects |= Q(product__sub_category__in=offer.sub_categories.all())
            has_conditions = True

        if not has_conditions:
            return queryset.none()

        return queryset.filter(q_objects).distinct()


class ProductReviewFilter(django_filters.FilterSet):
    rating = django_filters.NumberFilter(field_name="rating", lookup_expr="exact")

    class Meta:
        model = ProductReview
        fields = ["rating"]
