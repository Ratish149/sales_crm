from django.db import models, transaction
from rest_framework import serializers

from customer.serializers import CustomerSerializer
from customer.utils import get_customer_from_request
from product.models import Product, ProductVariant
from product.serializers import ProductOnlySerializer, ProductVariantSerializer
from promo_code.models import PromoCode

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
            "is_manual",
            "promo_code",
            "payment_type",
            "items",  # for creating/updating
            "order_items",  # for reading back
        ]
        read_only_fields = ["order_number", "created_at", "updated_at"]

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

            # Increment used_count for promo code if one was used
            if order.promo_code:
                PromoCode.objects.filter(id=order.promo_code.id).update(
                    used_count=models.F("used_count") + 1
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
            "is_manual",
            "payment_type",
        ]
