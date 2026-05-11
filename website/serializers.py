# serializers.py
from rest_framework import serializers

from product.models import (
    Category,
    PricingMetric,
    Product,
    ProductComposition,
    ProductOption,
    ProductOptionValue,
    ProductVariant,
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


class BulkProductVariantSerializer(serializers.Serializer):
    price = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    stock = serializers.IntegerField(default=0)
    options = serializers.DictField(
        child=serializers.CharField(),
        required=False,
        default=dict,
    )
    # No image support in bulk — files can't be sent via JSON


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
    variants = BulkProductVariantSerializer(many=True, required=False)

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
            "variants",
        ]

    def validate_variants(self, value):
        for idx, variant in enumerate(value):
            options = variant.get("options", {})
            if not isinstance(options, dict):
                raise serializers.ValidationError(
                    f"Variant at index {idx}: 'options' must be a dictionary "
                    f'e.g. {{"Size": "M", "Color": "Black"}}'
                )
        return value

    def create(self, validated_data):
        compositions_data = validated_data.pop("compositions", [])
        variants_data = validated_data.pop("variants", [])

        product = Product.objects.create(**validated_data)

        for comp in compositions_data:
            ProductComposition.objects.create(
                product=product,
                metric=comp["metric"],
                quantity=comp["quantity"],
            )

        for variant_data in variants_data:
            variant_data = dict(variant_data)
            options = variant_data.pop("options", {})

            variant = ProductVariant.objects.create(product=product, **variant_data)

            option_value_ids = []
            for option_name, value_name in options.items():
                option, _ = ProductOption.objects.get_or_create(
                    product=product, name=option_name
                )
                value, _ = ProductOptionValue.objects.get_or_create(
                    option=option, value=value_name
                )
                option_value_ids.append(value.id)

            variant.option_values.set(option_value_ids)

        return product
