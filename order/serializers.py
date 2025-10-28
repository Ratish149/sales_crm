from django.db import models, transaction
from rest_framework import serializers

from customer.serializers import CustomerSerializer
from customer.utils import get_customer_from_request
from product.models import Product, ProductVariant
from product.serializers import ProductOnlySerializer, ProductVariantSerializer

from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source="product",
        required=False,
        allow_null=True,
    )
    variant_id = serializers.PrimaryKeyRelatedField(
        queryset=ProductVariant.objects.all(),
        source="variant",
        required=False,
        allow_null=True,
    )

    class Meta:
        model = OrderItem
        fields = ["id", "product_id", "variant_id", "quantity", "price"]

    def validate(self, data):
        if not data.get("product") and not data.get("variant"):
            raise serializers.ValidationError(
                "Either product_id or variant_id must be provided"
            )
        if data.get("product") and data.get("variant"):
            raise serializers.ValidationError(
                "Cannot specify both product_id and variant_id"
            )
        return data


class OrderItemDetailSerializer(serializers.ModelSerializer):
    product = ProductOnlySerializer(read_only=True)
    variant = ProductVariantSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "product", "variant", "quantity", "price"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, write_only=True)
    order_items = OrderItemDetailSerializer(source="items", many=True, read_only=True)
    customer_details = CustomerSerializer(source="customer", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "customer",
            "customer_details",
            "order_number",
            "customer_name",
            "customer_email",
            "customer_phone",
            "customer_address",
            "shipping_address",
            "total_amount",
            "status",
            "transaction_id",
            "created_at",
            "updated_at",
            "is_paid",
            "payment_type",
            "items",  # for creating/updating
            "order_items",  # for reading back
        ]
        read_only_fields = ["order_number", "created_at", "updated_at"]

    def validate(self, data):
        """
        Validate that there is sufficient stock for all items before creating the order.
        """
        items_data = data.get("items", [])
        if not items_data:
            raise serializers.ValidationError({"items": "No order items provided."})

        errors = {}

        for index, item_data in enumerate(items_data):
            product = item_data.get("product")
            variant = item_data.get("variant")
            quantity = item_data.get("quantity", 0)

            if not product and not variant:
                errors[f"items.{index}"] = (
                    "Either product or variant must be specified."
                )
                continue

            if variant:
                # Check variant stock
                if (
                    variant.track_stock
                    and variant.stock is not None
                    and variant.stock < quantity
                ):
                    errors[f"items.{index}"] = (
                        f"Insufficient stock for variant {variant.name}. Only {variant.stock} available."
                    )
            elif product:
                # Check product stock
                if (
                    product.track_stock
                    and product.stock is not None
                    and product.stock < quantity
                ):
                    errors[f"items.{index}"] = (
                        f"Insufficient stock for product {product.name}. Only {product.stock} available."
                    )

        if errors:
            raise serializers.ValidationError(errors)

        return data

    def create(self, validated_data):
        request = self.context.get("request")
        items_data = validated_data.pop("items", [])

        if not request or not request.user.is_authenticated:
            validated_data["customer"] = None

        # Try to find a Customer with the same email as the User
        customer = get_customer_from_request(self.context["request"])
        if customer:
            validated_data["customer"] = customer

        with transaction.atomic():
            # Validate stock again in case of race conditions
            for item_data in items_data:
                product = item_data.get("product")
                variant = item_data.get("variant")
                quantity = item_data["quantity"]

                if variant:
                    if variant.track_stock and variant.stock is not None:
                        if variant.stock < quantity:
                            raise serializers.ValidationError(
                                {
                                    "items": [
                                        f"Insufficient stock for variant {variant.name}. Only {variant.stock} available."
                                    ]
                                }
                            )
                        # Lock the variant row for update
                        variant = ProductVariant.objects.select_for_update().get(
                            pk=variant.pk
                        )
                elif product and product.track_stock and product.stock is not None:
                    if product.stock < quantity:
                        raise serializers.ValidationError(
                            {
                                "items": [
                                    f"Insufficient stock for product {product.name}. Only {product.stock} available."
                                ]
                            }
                        )
                    # Lock the product row for update
                    product = Product.objects.select_for_update().get(pk=product.pk)

            # Create the order after all validations pass
            order = Order.objects.create(**validated_data)

            # Now create order items and update stock
            for item_data in items_data:
                product = item_data.get("product")
                variant = item_data.get("variant")
                quantity = item_data["quantity"]

                # Create order item
                OrderItem.objects.create(order=order, **item_data)

                # Update stock based on whether it's a variant or base product
                if variant:
                    if variant.product.track_stock and variant.stock is not None:
                        ProductVariant.objects.filter(pk=variant.pk).update(
                            stock=models.F("stock") - quantity
                        )
                elif product and product.track_stock and product.stock is not None:
                    Product.objects.filter(pk=product.pk).update(
                        stock=models.F("stock") - quantity
                    )

            return order


class OrderListSerializer(serializers.ModelSerializer):
    order_items = OrderItemDetailSerializer(source="items", many=True, read_only=True)
    customer_details = CustomerSerializer(source="customer", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "customer_details",
            "order_number",
            "customer_name",
            "customer_email",
            "customer_phone",
            "customer_address",
            "shipping_address",
            "latitude",
            "longitude",
            "total_amount",
            "status",
            "order_items",
            "transaction_id",
            "created_at",
            "updated_at",
            "is_paid",
            "payment_type",
        ]
