from rest_framework import serializers

from cart.models import Cart, CartItem
from product.models import Product, ProductVariant
from product.serializers import ProductOnlySerializer


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductOnlySerializer(read_only=True)
    total_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = CartItem
        fields = [
            "id",
            "product",
            "variant",
            "quantity",
            "price",
            "total_price",
            "created_at",
            "updated_at",
        ]


class CartItemAddSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=False, allow_null=True)
    variant_id = serializers.IntegerField(required=False, allow_null=True)
    quantity = serializers.IntegerField(default=1, min_value=1)
    price = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )

    def validate(self, data):
        product_id = data.get("product_id")
        variant_id = data.get("variant_id")

        if not product_id and not variant_id:
            raise serializers.ValidationError(
                "Either product_id or variant_id must be provided."
            )

        product = None
        variant = None

        if variant_id:
            try:
                variant = ProductVariant.objects.select_related("product").get(
                    pk=variant_id
                )
                product = variant.product
            except ProductVariant.DoesNotExist:
                raise serializers.ValidationError({
                    "variant_id": f"ProductVariant with id {variant_id} does not exist."
                })

        if product_id:
            try:
                prod = Product.objects.get(pk=product_id)
                if product and product.pk != prod.pk:
                    raise serializers.ValidationError(
                        "Provided product_id does not match the variant's product."
                    )
                product = prod
            except Product.DoesNotExist:
                raise serializers.ValidationError({
                    "product_id": f"Product with id {product_id} does not exist."
                })

        data["product_obj"] = product
        data["variant_obj"] = variant
        return data


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    total_items = serializers.IntegerField(read_only=True)

    class Meta:
        model = Cart
        fields = [
            "id",
            "customer",
            "status",
            "contact_name",
            "contact_phone",
            "contact_email",
            "total_amount",
            "total_items",
            "last_activity_at",
            "abandoned_at",
            "recovered_at",
            "created_at",
            "updated_at",
            "items",
        ]
        read_only_fields = [
            "id",
            "status",
            "last_activity_at",
            "abandoned_at",
            "recovered_at",
            "created_at",
            "updated_at",
        ]


class CartContactUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cart
        fields = ["contact_name", "contact_phone", "contact_email"]
        extra_kwargs = {
            "contact_name": {"required": False, "allow_blank": True},
            "contact_phone": {"required": False, "allow_blank": True},
            "contact_email": {"required": False, "allow_blank": True},
        }


class AdminCartListSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    total_items = serializers.IntegerField(read_only=True)

    class Meta:
        model = Cart
        fields = [
            "id",
            "customer",
            "contact_name",
            "contact_phone",
            "contact_email",
            "status",
            "total_amount",
            "total_items",
            "last_activity_at",
            "abandoned_at",
            "recovered_at",
            "created_at",
            "updated_at",
            "items",
        ]
