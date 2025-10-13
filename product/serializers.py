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
        fields = ["id", "name"]


class ProductVariantReadSerializer(serializers.ModelSerializer):
    option_values = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = ["id", "price", "stock", "image", "option_values"]

    def get_option_values(self, obj):
        # Get all option values for this variant
        return {v.option.name: v.value for v in obj.option_values.all()}


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

    variant_images = serializers.DictField(
        child=serializers.FileField(), write_only=True, required=False, allow_empty=True
    )

    variants = ProductVariantWriteSerializer(many=True, write_only=True, required=False)
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
        import json

        # Create a mutable copy
        if hasattr(data, "_mutable"):
            data._mutable = True

        # Parse variants if it's a JSON string
        if "variants" in data and isinstance(data.get("variants"), str):
            try:
                data["variants"] = json.loads(data["variants"])
            except json.JSONDecodeError:
                pass

        # Collect variant images from individual form fields
        variant_images = {}
        keys_to_remove = []

        for key in list(data.keys()):
            if key.startswith("variant_image_"):
                # Extract the index: variant_image_0 -> variant_0
                index = key.replace("variant_image_", "")
                variant_key = f"variant_{index}"
                variant_images[variant_key] = data[key]
                keys_to_remove.append(key)

        # Remove the individual variant_image_* fields
        for key in keys_to_remove:
            data.pop(key, None)

        # Add the collected variant_images dict
        if variant_images:
            data["variant_images"] = variant_images

        return super().to_internal_value(data)

    def create(self, validated_data):
        image_files = validated_data.pop("image_files", [])
        variants_data = validated_data.pop("variants", [])
        variant_images = validated_data.pop("variant_images", {})

        # Check if product with same name exists
        name = validated_data.get("name")
        if name and Product.objects.filter(name=name).exists():
            raise serializers.ValidationError("Product with this name already exists.")

        product = Product.objects.create(**validated_data)

        # Create images
        for img in image_files:
            ProductImage.objects.create(product=product, image=img)

        # Create variants
        for variant_data in variants_data:
            options = variant_data.pop("options", {})
            image_key = variant_data.pop("image", None)

            # Handle the variant image
            if image_key and image_key in variant_images:
                variant_data["image"] = variant_images[image_key]
            else:
                # Remove image key if not found to avoid validation error
                variant_data.pop("image", None)

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
            # Delete old variants and their associated option values
            instance.variants.all().delete()

            # Also clean up orphaned options (options with no values)
            for option in instance.productoption_set.all():
                if not option.productoptionvalue_set.exists():
                    option.delete()

            for variant_data in variants_data:
                options = variant_data.pop("options", {})
                image_key = variant_data.pop("image", None)

                # Handle the variant image
                if image_key and variant_images and image_key in variant_images:
                    variant_data["image"] = variant_images[image_key]
                else:
                    # Remove image key if not found
                    variant_data.pop("image", None)

                variant = ProductVariant.objects.create(
                    product=instance, **variant_data
                )

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

        return instance


class ProductSmallSerializer(serializers.ModelSerializer):
    sub_category = SubCategorySmallSerializer(read_only=True)
    category = CategorySmallSerializer(read_only=True)
    reviews_count = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    is_wishlist = serializers.SerializerMethodField()

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
            "average_rating",
            "reviews_count",
            "is_wishlist",
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
