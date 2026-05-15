import json

from django.core.files.base import File
from django.db import models
from rest_framework import serializers

from customer.serializers import CustomerSerializer
from customer.utils import get_customer_from_request

from .models import (
    Category,
    PricingMetric,
    Product,
    ProductComposition,
    ProductImage,
    ProductOffer,
    ProductOption,
    ProductOptionValue,
    ProductReview,
    ProductVariant,
    SubCategory,
    Wishlist,
)


class PricingMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = PricingMetric
        fields = [
            "id",
            "name",
            "price_per_unit",
            "unit",
            "last_updated",
        ]  # explicit, was __all__


class ProductOfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductOffer
        fields = [
            "id",
            "name",
            "description",
            "offer_type",
            "discount_value",
            "start_date",
            "end_date",
            "is_valid",
        ]


class ProductCompositionSerializer(serializers.ModelSerializer):
    metric_detail = PricingMetricSerializer(source="metric", read_only=True)

    class Meta:
        model = ProductComposition
        fields = [
            "id",
            "metric",
            "metric_detail",
            "quantity",
        ]  # unchanged, already explicit


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = [
            "id",
            "product",
            "image",
            "created_at",
            "updated_at",
        ]  # explicit, was __all__


class ProductImageSmallSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image"]  # unchanged


class SubCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SubCategory
        fields = [
            "id",
            "category",
            "name",
            "slug",
            "description",
            "image",
            "created_at",
            "updated_at",
        ]  # explicit, was __all__


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "image",
            "created_at",
            "updated_at",
        ]  # explicit, was __all__


class CategorySmallSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
        ]  # unchanged (the second definition wins, this is correct)


class SubCategorySmallSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubCategory
        fields = ["id", "name", "slug", "description", "image"]  # unchanged


class SubCategoryDetailSerializer(serializers.ModelSerializer):
    category = CategorySmallSerializer(read_only=True)

    class Meta:
        model = SubCategory
        fields = ["id", "name", "slug", "description", "image", "category"]  # unchanged


class ProductOptionValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductOptionValue
        fields = ["id", "value"]  # unchanged


class ProductOptionSerializer(serializers.ModelSerializer):
    values = ProductOptionValueSerializer(
        many=True, read_only=True, source="productoptionvalue_set"
    )

    class Meta:
        model = ProductOption
        fields = ["id", "name", "values"]  # unchanged


class ProductVariantWriteSerializer(serializers.Serializer):
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    stock = serializers.IntegerField(default=0)
    image = serializers.FileField(required=False, allow_null=True)
    options = serializers.DictField(child=serializers.CharField(), required=False)


class ProductVariantReadSerializer(serializers.ModelSerializer):
    option_values = serializers.SerializerMethodField()
    active_offer = ProductOfferSerializer(read_only=True)
    discounted_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = ProductVariant
        fields = [
            "id",
            "price",
            "discounted_price",
            "active_offer",
            "stock",
            "image",
            "option_values",
        ]

    def get_option_values(self, obj):
        return {v.option.name: v.value for v in obj.option_values.all()}


class VariantsField(serializers.Field):
    def to_internal_value(self, data):
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError as e:
                raise serializers.ValidationError(f"Invalid JSON format: {str(e)}")
        if not isinstance(data, list):
            raise serializers.ValidationError("Variants must be a list")
        return data

    def to_representation(self, value):
        return value


class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSmallSerializer(many=True, read_only=True)
    category = CategorySmallSerializer(read_only=True)
    sub_category = SubCategorySmallSerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.only("id"),  # only pk needed for validation
        source="category",
        write_only=True,
        allow_null=True,
        required=False,
    )
    sub_category_id = serializers.PrimaryKeyRelatedField(
        queryset=SubCategory.objects.only("id"),  # only pk needed for validation
        source="sub_category",
        write_only=True,
        allow_null=True,
        required=False,
    )
    image_files = serializers.ListField(
        child=serializers.FileField(), write_only=True, required=False, allow_empty=True
    )
    variant_images = serializers.DictField(
        child=serializers.FileField(), write_only=True, required=False, allow_empty=True
    )
    variants = VariantsField(write_only=True, required=False)
    variants_read = ProductVariantReadSerializer(
        source="variants", many=True, read_only=True
    )
    options = serializers.SerializerMethodField(read_only=True)
    compositions = ProductCompositionSerializer(many=True, required=False)
    final_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    active_offer = ProductOfferSerializer(read_only=True)
    discounted_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "price",
            "market_price",
            "track_stock",
            "stock",
            "weight",
            "thumbnail_image",
            "thumbnail_alt_description",
            "category",
            "sub_category",
            "category_id",
            "sub_category_id",
            "is_popular",
            "is_featured",
            "status",
            "fast_shipping",
            "warranty",
            "meta_title",
            "meta_description",
            "images",
            "image_files",
            "variant_images",
            "options",
            "variants",
            "variants_read",
            "use_dynamic_pricing",
            "base_making_charge",
            "compositions",
            "final_price",
            "discounted_price",
            "active_offer",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {"slug": {"read_only": True}}

    def get_options(self, obj):
        # uses prefetched productoption_set — no extra queries when queryset is optimized
        options = obj.productoption_set.prefetch_related("productoptionvalue_set").all()
        options_data = []
        for option in options:
            values = option.productoptionvalue_set.all()
            options_data.append({
                "id": option.id,
                "name": option.name,
                "values": ProductOptionValueSerializer(values, many=True).data,
            })
        return options_data

    # to_internal_value, validate_variants, create, update — all unchanged
    def to_internal_value(self, data):
        self._variant_images_temp = {}
        self._compositions_temp = None
        self._options_temp = None

        if hasattr(data, "_mutable"):
            data._mutable = True
        if hasattr(data, "copy"):
            data = data.copy()
        else:
            data = dict(data)

        keys_to_remove = []
        for key in list(data.keys()):
            if key.startswith("variant_image_"):
                index = key.replace("variant_image_", "")
                variant_key = f"variant_image_{index}"
                self._variant_images_temp[variant_key] = data[key]
                keys_to_remove.append(key)
        for key in keys_to_remove:
            data.pop(key, None)

        if "compositions" in data and isinstance(data["compositions"], str):
            try:
                self._compositions_temp = json.loads(data["compositions"])
            except (json.JSONDecodeError, TypeError):
                pass
            data.pop("compositions", None)

        if "options" in data:
            if isinstance(data["options"], str):
                try:
                    self._options_temp = json.loads(data["options"])
                except (json.JSONDecodeError, TypeError):
                    pass
            elif isinstance(data["options"], list):
                self._options_temp = data["options"]
            data.pop("options", None)

        validated = super().to_internal_value(data)

        if self._variant_images_temp:
            validated["variant_images"] = self._variant_images_temp
        if self._compositions_temp is not None:
            validated["compositions"] = self._compositions_temp
        if self._options_temp is not None:
            validated["options"] = self._options_temp

        return validated

    def validate_variants(self, value):
        if not value:
            return value
        for idx, variant in enumerate(value):
            if "options" not in variant:
                raise serializers.ValidationError(
                    f"Variant at index {idx} is missing 'options' field"
                )
            if not isinstance(variant.get("options"), dict):
                raise serializers.ValidationError(
                    f"Variant at index {idx} 'options' must be a dictionary"
                )
        return value

    def create(self, validated_data):
        image_files = validated_data.pop("image_files", [])
        variants_data = validated_data.pop("variants", [])
        variant_images = validated_data.pop("variant_images", {})
        compositions_data = validated_data.pop("compositions", [])
        options_data = validated_data.pop("options", [])

        product = Product.objects.create(**validated_data)

        for comp_data in compositions_data:
            metric_id = comp_data.get("metric")
            quantity = comp_data.get("quantity")
            if metric_id and quantity is not None:
                ProductComposition.objects.create(
                    product=product,
                    metric_id=metric_id,
                    quantity=quantity,
                )

        for img in image_files:
            ProductImage.objects.create(product=product, image=img)

        # Create options and values if provided
        for opt_data in options_data:
            name = opt_data.get("name")
            values = opt_data.get("values", [])
            if name:
                option, _ = ProductOption.objects.get_or_create(
                    product=product, name=name
                )
                for val in values:
                    ProductOptionValue.objects.get_or_create(option=option, value=val)

        for idx, variant_data in enumerate(variants_data):
            try:
                variant_dict = dict(variant_data)
                options = variant_dict.pop("options", {})
                image_key = variant_dict.pop("image", None)

                if image_key and image_key in variant_images:
                    variant_dict["image"] = variant_images[image_key]

                variant = ProductVariant.objects.create(product=product, **variant_dict)

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
            except Exception:
                raise serializers.ValidationError("Failed to create variant")

        return product

    def update(self, instance, validated_data):
        image_files = validated_data.pop("image_files", None)
        variants_data = validated_data.pop("variants", None)
        variant_images = validated_data.pop("variant_images", None)
        compositions_data = validated_data.pop("compositions", None)
        options_data = validated_data.pop("options", None)

        name = validated_data.get("name")
        if (
            name
            and name != instance.name
            and Product.objects.filter(name=name).exists()
        ):
            raise serializers.ValidationError("Product with this name already exists.")

        instance = super().update(instance, validated_data)

        if options_data is not None:
            provided_option_names = [
                opt["name"] for opt in options_data if opt.get("name")
            ]
            # Delete options not in the provided list
            instance.productoption_set.exclude(name__in=provided_option_names).delete()

            for opt_data in options_data:
                name = opt_data.get("name")
                values = opt_data.get("values", [])
                if name:
                    option, _ = ProductOption.objects.get_or_create(
                        product=instance, name=name
                    )
                    # Delete values for this option not in the provided list
                    option.productoptionvalue_set.exclude(value__in=values).delete()
                    for val in values:
                        ProductOptionValue.objects.get_or_create(
                            option=option, value=val
                        )

        if compositions_data is not None:
            instance.compositions.all().delete()
            for comp_data in compositions_data:
                metric = comp_data.get("metric")
                quantity = comp_data.get("quantity")
                if metric and quantity is not None:
                    if isinstance(metric, PricingMetric):
                        ProductComposition.objects.create(
                            product=instance,
                            metric=metric,
                            quantity=quantity,
                        )
                    else:
                        ProductComposition.objects.create(
                            product=instance,
                            metric_id=metric,
                            quantity=quantity,
                        )

        if image_files is not None:
            for img in image_files:
                ProductImage.objects.create(product=instance, image=img)

        if variants_data is not None:
            # We don't need the partial cleanup here anymore as we do it at the end

            existing_variants = {}
            for variant in instance.variants.all():
                option_values = {}
                for option_value in variant.option_values.all():
                    option_values[option_value.option.name] = option_value.value
                if option_values:
                    existing_variants[frozenset(option_values.items())] = variant

            updated_option_sets = set()

            for variant_data in variants_data:
                try:
                    variant_dict = dict(variant_data)
                    options = variant_dict.pop("options", {})
                    image_key = variant_dict.pop("image", None)

                    if image_key:
                        if variant_images and image_key in variant_images:
                            variant_dict["image"] = variant_images[image_key]
                        elif isinstance(image_key, str) and not isinstance(
                            image_key, File
                        ):
                            pass
                        else:
                            variant_dict["image"] = image_key

                    option_set = frozenset(options.items())
                    updated_option_sets.add(option_set)

                    variant = existing_variants.get(option_set)

                    if variant:
                        for attr, value in variant_dict.items():
                            setattr(variant, attr, value)
                        variant.save()
                    else:
                        variant = instance.variants.create(**variant_dict)

                    option_value_ids = []
                    for option_name, value_name in options.items():
                        option, _ = ProductOption.objects.get_or_create(
                            product=instance, name=option_name
                        )
                        value, _ = ProductOptionValue.objects.get_or_create(
                            option=option, value=value_name
                        )
                        option_value_ids.append(value.id)
                    variant.option_values.set(option_value_ids)

                except Exception as e:
                    raise serializers.ValidationError(
                        f"Failed to update/create variant: {str(e)}"
                    )

            for variant in instance.variants.all():
                variant_options = {}
                for option_value in variant.option_values.all():
                    variant_options[option_value.option.name] = option_value.value
                if (
                    variant_options
                    and frozenset(variant_options.items()) not in updated_option_sets
                ):
                    variant.delete()

            # Cleanup stale options and values that are not used by any variant
            # and were not explicitly provided in options_data (if options_data was provided, we already synced)
            if options_data is None:
                # 1. Delete option values that are not linked to any variant of this product
                ProductOptionValue.objects.filter(option__product=instance).exclude(
                    variants__in=instance.variants.all()
                ).delete()

                # 2. Delete options that have no values remaining
                ProductOption.objects.filter(product=instance).annotate(
                    value_count=models.Count("productoptionvalue_set")
                ).filter(value_count=0).delete()

        return instance


class ProductSmallSerializer(serializers.ModelSerializer):
    sub_category = SubCategorySmallSerializer(read_only=True)
    category = CategorySmallSerializer(read_only=True)
    reviews_count = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    is_wishlist = serializers.SerializerMethodField()
    variants_read = ProductVariantReadSerializer(
        source="variants", many=True, read_only=True
    )
    final_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    active_offer = ProductOfferSerializer(read_only=True)
    discounted_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

    def get_reviews_count(self, obj):
        # use annotated value if available (from queryset), else fall back to query
        if hasattr(obj, "reviews_count_annotated"):
            return obj.reviews_count_annotated
        return ProductReview.objects.filter(product=obj).count()

    def get_average_rating(self, obj):
        # use annotated value if available (from queryset), else fall back to query
        if hasattr(obj, "average_rating"):
            return obj.average_rating or 0
        return (
            ProductReview.objects.filter(product=obj).aggregate(
                avg_rating=models.Avg("rating")
            )["avg_rating"]
            or 0
        )

    def get_is_wishlist(self, obj):
        user = get_customer_from_request(self.context["request"])
        if not user:
            return False
        return Wishlist.objects.filter(user=user, product=obj).exists()

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "price",
            "market_price",
            "stock",
            "thumbnail_image",
            "thumbnail_alt_description",
            "category",
            "sub_category",
            "is_popular",
            "is_featured",
            "created_at",
            "updated_at",
            "fast_shipping",
            "warranty",
            "average_rating",
            "reviews_count",
            "is_wishlist",
            "variants_read",
            "final_price",
            "discounted_price",
            "active_offer",
            "use_dynamic_pricing",
        ]


class ProductOnlySerializer(serializers.ModelSerializer):
    final_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    active_offer = ProductOfferSerializer(read_only=True)
    discounted_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "price",
            "market_price",
            "final_price",
            "discounted_price",
            "active_offer",
            "thumbnail_image",
            "thumbnail_alt_description",
        ]  # unchanged


class ProductVariantSerializer(serializers.ModelSerializer):
    option_values = ProductOptionValueSerializer(many=True, read_only=True)
    product = ProductOnlySerializer(read_only=True)

    class Meta:
        model = ProductVariant
        fields = [
            "id",
            "product",
            "price",
            "stock",
            "image",
            "option_values",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]  # unchanged


class ProductReviewSerializer(serializers.ModelSerializer):
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.only("id"),  # only pk needed for validation
        write_only=True,
        source="product",
    )
    product = ProductSmallSerializer(read_only=True)
    user = CustomerSerializer(read_only=True)

    class Meta:
        model = ProductReview
        fields = [
            "id",
            "product_id",
            "user_id",
            "product",
            "user",
            "review",
            "rating",
            "created_at",
            "updated_at",
        ]


class ProductReviewDetailSerializer(serializers.ModelSerializer):
    product = ProductSmallSerializer(read_only=True)
    user = CustomerSerializer(read_only=True)

    class Meta:
        model = ProductReview
        fields = ["id", "product", "user", "review", "rating", "created_at"]


class WishlistSerializer(serializers.ModelSerializer):
    product = ProductSmallSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.only("id"),  # only pk needed for validation
        write_only=True,
        source="product",
    )

    class Meta:
        model = Wishlist
        fields = ["id", "user", "product", "product_id", "created_at", "updated_at"]


class BulkUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    zip_file = serializers.FileField(required=False, allow_null=True)


class ProductVariantAsProductSerializer(serializers.ModelSerializer):
    # all fields unchanged — no __all__ usage here
    id = serializers.IntegerField(read_only=True)
    name = serializers.SerializerMethodField()
    slug = serializers.CharField(source="product.slug", read_only=True)
    price = serializers.SerializerMethodField()
    market_price = serializers.SerializerMethodField()
    final_price = serializers.SerializerMethodField()
    thumbnail_image = serializers.SerializerMethodField()
    thumbnail_alt_description = serializers.CharField(
        source="product.thumbnail_alt_description", read_only=True
    )
    category = CategorySmallSerializer(source="product.category", read_only=True)
    sub_category = SubCategorySmallSerializer(
        source="product.sub_category", read_only=True
    )
    is_popular = serializers.BooleanField(source="product.is_popular", read_only=True)
    is_featured = serializers.BooleanField(source="product.is_featured", read_only=True)
    created_at = serializers.DateTimeField(source="product.created_at", read_only=True)
    updated_at = serializers.DateTimeField(source="product.updated_at", read_only=True)
    fast_shipping = serializers.BooleanField(
        source="product.fast_shipping", read_only=True
    )
    warranty = serializers.BooleanField(source="product.warranty", read_only=True)
    average_rating = serializers.SerializerMethodField()
    reviews_count = serializers.SerializerMethodField()
    is_wishlist = serializers.SerializerMethodField()
    variants_read = ProductVariantReadSerializer(
        source="product.variants", many=True, read_only=True
    )
    active_offer = ProductOfferSerializer(source="product.active_offer", read_only=True)
    discounted_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    use_dynamic_pricing = serializers.BooleanField(
        source="product.use_dynamic_pricing", read_only=True
    )

    class Meta:
        model = ProductVariant
        fields = [
            "id",
            "name",
            "slug",
            "price",
            "market_price",
            "stock",
            "thumbnail_image",
            "thumbnail_alt_description",
            "category",
            "sub_category",
            "is_popular",
            "is_featured",
            "created_at",
            "updated_at",
            "fast_shipping",
            "warranty",
            "average_rating",
            "reviews_count",
            "is_wishlist",
            "variants_read",
            "final_price",
            "discounted_price",
            "active_offer",
            "use_dynamic_pricing",
        ]

    def get_name(self, obj):
        options = [v.value for v in obj.option_values.all()]
        options_str = " ".join(options)
        if options_str:
            return f"{obj.product.name} ({options_str})"
        return obj.product.name

    def get_price(self, obj):
        return obj.price if obj.price is not None else obj.product.price

    def get_market_price(self, obj):
        return obj.price if obj.price is not None else obj.product.market_price

    def get_final_price(self, obj):
        return obj.price if obj.price is not None else obj.product.final_price

    def get_thumbnail_image(self, obj):
        request = self.context.get("request")
        image = obj.image if obj.image else obj.product.thumbnail_image
        if image and hasattr(image, "url"):
            return request.build_absolute_uri(image.url) if request else image.url
        return None

    def get_reviews_count(self, obj):
        return ProductReview.objects.filter(product=obj.product).count()

    def get_average_rating(self, obj):
        return (
            ProductReview.objects.filter(product=obj.product).aggregate(
                avg_rating=models.Avg("rating")
            )["avg_rating"]
            or 0
        )

    def get_is_wishlist(self, obj):
        request = self.context.get("request")
        if not request:
            return False
        user = get_customer_from_request(request)
        if not user:
            return False
        return Wishlist.objects.filter(user=user, product=obj.product).exists()


class UnifiedProductListingSerializer(serializers.Serializer):
    def to_representation(self, instance):
        from .models import Product, ProductVariant

        if isinstance(instance, ProductVariant):
            return ProductVariantAsProductSerializer(
                instance, context=self.context
            ).data
        elif isinstance(instance, Product):
            return ProductSmallSerializer(instance, context=self.context).data
        return super().to_representation(instance)
