import json

from django.core.files.base import File
from django.db.models import Avg
from rest_framework import serializers

from customer.serializers import CustomerSerializer
from customer.utils import get_customer_from_request

from .models import (
    Category,
    Product,
    ProductImage,
    ProductOption,
    ProductOptionValue,
    ProductReview,
    ProductVariant,
    SubCategory,
    Wishlist,
)


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = "__all__"


class ProductImageSmallSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image"]


class SubCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SubCategory
        fields = "__all__"


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"


class CategorySmallSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "description", "image"]


class SubCategorySmallSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubCategory
        fields = ["id", "name", "slug", "description", "image"]


class SubCategoryDetailSerializer(serializers.ModelSerializer):
    category = CategorySmallSerializer(read_only=True)

    class Meta:
        model = SubCategory
        fields = ["id", "name", "slug", "description", "image", "category"]


class ProductOptionValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductOptionValue
        fields = [
            "id",
            "value",
        ]


class ProductOptionSerializer(serializers.ModelSerializer):
    values = ProductOptionValueSerializer(
        many=True, read_only=True, source="productoptionvalue_set"
    )

    class Meta:
        model = ProductOption
        fields = ["id", "name", "values"]


class ProductVariantWriteSerializer(serializers.Serializer):
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    stock = serializers.IntegerField(default=0)
    image = serializers.FileField(required=False, allow_null=True)
    options = serializers.DictField(child=serializers.CharField(), required=False)


class CategorySmallSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug"]


class ProductVariantReadSerializer(serializers.ModelSerializer):
    option_values = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = ["id", "price", "stock", "image", "option_values"]

    def get_option_values(self, obj):
        # Get all option values for this variant
        return {v.option.name: v.value for v in obj.option_values.all()}


class VariantsField(serializers.Field):
    """Custom field to handle variants as either JSON string or list"""

    def to_internal_value(self, data):
        # If it's a string, parse it
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError as e:
                raise serializers.ValidationError(f"Invalid JSON format: {str(e)}")

        # Now it should be a list
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
        queryset=Category.objects.all(),
        source="category",
        write_only=True,
        allow_null=True,
        required=False,
    )
    sub_category_id = serializers.PrimaryKeyRelatedField(
        queryset=SubCategory.objects.all(),
        source="sub_category",
        write_only=True,
        allow_null=True,
        required=False,
    )
    image_files = serializers.ListField(
        child=serializers.FileField(), write_only=True, required=False, allow_empty=True
    )

    # Remove DictField validation - we'll handle it manually
    variant_images = serializers.DictField(
        child=serializers.FileField(), write_only=True, required=False, allow_empty=True
    )

    variants = VariantsField(write_only=True, required=False)
    variants_read = ProductVariantReadSerializer(
        source="variants", many=True, read_only=True
    )
    options = serializers.SerializerMethodField(read_only=True)

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
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {"slug": {"read_only": True}}

    def get_options(self, obj):
        """Get all options with their values for the product"""
        options = obj.productoption_set.prefetch_related("productoptionvalue_set").all()
        options_data = []

        for option in options:
            values = option.productoptionvalue_set.all()
            options_data.append(
                {
                    "id": option.id,
                    "name": option.name,
                    "values": ProductOptionValueSerializer(values, many=True).data,
                }
            )

        return options_data

    def to_internal_value(self, data):
        """
        Custom method to handle FormData with variant_image_* fields
        and JSON string for variants
        """
        # Store variant images before validation
        self._variant_images_temp = {}

        # Create a mutable copy if needed
        if hasattr(data, "_mutable"):
            data._mutable = True

        # Make a copy to avoid modifying original
        if hasattr(data, "copy"):
            data = data.copy()
        else:
            data = dict(data)

        # Collect variant images from individual form fields
        keys_to_remove = []

        # First pass: collect all variant_image_* fields
        for key in list(data.keys()):
            if key.startswith("variant_image_"):
                # Extract the index: variant_image_0 -> variant_0
                index = key.replace("variant_image_", "")
                variant_key = f"variant_image_{index}"  # Keep the full key name
                self._variant_images_temp[variant_key] = data[key]
                keys_to_remove.append(key)

        # Remove the individual variant_image_* fields from data
        for key in keys_to_remove:
            data.pop(key, None)

        # Don't add variant_images to data - we'll handle it separately
        # This avoids DictField validation issues

        # Call parent to do normal validation
        validated = super().to_internal_value(data)

        # Add our collected variant images to validated data
        if self._variant_images_temp:
            validated["variant_images"] = self._variant_images_temp

        return validated

    def validate_variants(self, value):
        """Validate variants structure"""
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

        product = Product.objects.create(**validated_data)

        # Create images
        for img in image_files:
            ProductImage.objects.create(product=product, image=img)

        # Create variants
        for idx, variant_data in enumerate(variants_data):
            try:
                # Make a copy to avoid modifying the original
                variant_dict = dict(variant_data)

                # Extract options and image key
                options = variant_dict.pop("options", {})
                image_key = variant_dict.pop("image", None)

                # Handle the variant image - assign the actual file
                if image_key and image_key in variant_images:
                    variant_dict["image"] = variant_images[image_key]

                # Create the variant with the image
                variant = ProductVariant.objects.create(product=product, **variant_dict)

                # Create options and values
                option_value_ids = []
                for option_name, value_name in options.items():
                    option, _ = ProductOption.objects.get_or_create(
                        product=product, name=option_name
                    )
                    value, _ = ProductOptionValue.objects.get_or_create(
                        option=option, value=value_name
                    )
                    option_value_ids.append(value.id)

                # Link option values to variant
                variant.option_values.set(option_value_ids)

            except Exception:
                raise serializers.ValidationError("Failed to create variant")
                continue

        return product

    def update(self, instance, validated_data):
        image_files = validated_data.pop("image_files", None)
        variants_data = validated_data.pop("variants", None)
        variant_images = validated_data.pop("variant_images", None)

        # Check if product with same name exists (excluding current instance)
        name = validated_data.get("name")
        if (
            name
            and name != instance.name
            and Product.objects.filter(name=name).exists()
        ):
            raise serializers.ValidationError("Product with this name already exists.")

        instance = super().update(instance, validated_data)

        if image_files is not None:
            instance.images.all().delete()
            for img in image_files:
                ProductImage.objects.create(product=instance, image=img)

        if variants_data is not None:
            # Clean up orphaned options
            for option in instance.productoption_set.all():
                if not option.productoptionvalue_set.exists():
                    option.delete()

            # Create a mapping of existing variants by their options
            existing_variants = {}
            for variant in instance.variants.all():
                option_values = {}
                for option_value in variant.option_values.all():
                    option_values[option_value.option.name] = option_value.value
                if option_values:  # Only add variants with options to the mapping
                    existing_variants[frozenset(option_values.items())] = variant

            updated_option_sets = set()

            # Update or create variants
            for variant_data in variants_data:
                try:
                    variant_dict = dict(variant_data)
                    options = variant_dict.pop("options", {})
                    image_key = variant_dict.pop("image", None)

                    # Handle the variant image
                    if image_key:
                        if variant_images and image_key in variant_images:
                            # New image file from form data
                            variant_dict["image"] = variant_images[image_key]
                        elif isinstance(image_key, str) and not isinstance(
                            image_key, File
                        ):
                            # It's a URL string - don't add to variant_dict
                            # This prevents Django from treating it as a new file path
                            pass
                        else:
                            # It's already a File object, use it
                            variant_dict["image"] = image_key

                    # Create a key from the options to find matching variants
                    option_set = frozenset(options.items())
                    updated_option_sets.add(option_set)

                    # Try to find existing variant with the same options
                    variant = existing_variants.get(option_set)

                    if variant:
                        # Update existing variant
                        for attr, value in variant_dict.items():
                            setattr(variant, attr, value)
                        variant.save()
                    else:
                        # Create new variant
                        variant = instance.variants.create(**variant_dict)

                    # Update options for the variant
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

            # Delete variants that were not in the update data
            for variant in instance.variants.all():
                variant_options = {}
                for option_value in variant.option_values.all():
                    variant_options[option_value.option.name] = option_value.value

                # Check if this variant's options are in the updated options
                if (
                    variant_options
                    and frozenset(variant_options.items()) not in updated_option_sets
                ):
                    variant.delete()

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

    def get_reviews_count(self, obj):
        return ProductReview.objects.only("id").filter(product=obj).count()

    def get_average_rating(self, obj):
        return (
            ProductReview.objects.only("id")
            .filter(product=obj)
            .aggregate(avg_rating=Avg("rating"))["avg_rating"]
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
        ]


class ProductOnlySerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "price",
            "market_price",
            "thumbnail_image",
            "thumbnail_alt_description",
        ]


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
        read_only_fields = ["created_at", "updated_at"]


class ProductReviewSerializer(serializers.ModelSerializer):
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), write_only=True, source="product"
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
        queryset=Product.objects.all(), write_only=True, source="product"
    )

    class Meta:
        model = Wishlist
        fields = ["id", "user", "product", "product_id", "created_at", "updated_at"]


class BulkUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
