# serializers.py
from rest_framework import serializers

from product.models import (
    Category,
    PricingMetric,
    Product,
    ProductComposition,
    SubCategory,
)

from .models import Page, PageComponent, SiteConfig, Theme


class SiteConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteConfig
        fields = "__all__"


class ThemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Theme
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "published_version")


class PageComponentSerializer(serializers.ModelSerializer):
    page_slug = serializers.CharField(source="page.slug", read_only=True)

    class Meta:
        model = PageComponent
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "published_version")


class PageSerializer(serializers.ModelSerializer):
    components = PageComponentSerializer(many=True, read_only=True)

    class Meta:
        model = Page
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "published_version")


class PageListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Page
        fields = (
            "id",
            "title",
            "slug",
            "status",
            "theme",
            "meta_title",
            "meta_description",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at", "published_version")


class BulkProductCompositionSerializer(serializers.Serializer):
    metric = serializers.PrimaryKeyRelatedField(queryset=PricingMetric.objects.all())
    quantity = serializers.DecimalField(max_digits=10, decimal_places=3)


class BulkProductCreateSerializer(serializers.ModelSerializer):
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source="category",
        allow_null=True,
        required=False,
    )
    sub_category_id = serializers.PrimaryKeyRelatedField(
        queryset=SubCategory.objects.all(),
        source="sub_category",
        allow_null=True,
        required=False,
    )
    compositions = BulkProductCompositionSerializer(many=True, required=False)

    class Meta:
        model = Product
        fields = [
            "name",
            "description",
            "price",
            "market_price",
            "stock",
            "track_stock",
            "weight",
            "category_id",
            "sub_category_id",
            "is_popular",
            "is_featured",
            "fast_shipping",
            "warranty",
            "status",
            "meta_title",
            "meta_description",
            "use_dynamic_pricing",
            "base_making_charge",
            "compositions",
        ]

    def create(self, validated_data):
        compositions_data = validated_data.pop("compositions", [])

        product = Product.objects.create(**validated_data)

        for comp in compositions_data:
            ProductComposition.objects.create(
                product=product,
                metric=comp[
                    "metric"
                ],  # PricingMetric instance, resolved by PrimaryKeyRelatedField
                quantity=comp["quantity"],
            )

        return product
