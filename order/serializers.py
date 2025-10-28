from rest_framework import serializers

from customer.serializers import CustomerSerializer
from customer.utils import get_customer_from_request
from product.models import Product
from product.serializers import ProductOnlySerializer

from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source="product"
    )

    class Meta:
        model = OrderItem
        fields = ["id", "product_id", "quantity", "price"]


class OrderItemDetailSerializer(serializers.ModelSerializer):
    product = ProductOnlySerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "product", "quantity", "price"]


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
        # Decode JWT manually
        customer = get_customer_from_request(self.context["request"])
        if customer:
            validated_data["customer"] = customer

        order = Order.objects.create(**validated_data)

        # Now create order items
        for item_data in items_data:
            OrderItem.objects.create(order=order, **item_data)

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
            "total_amount",
            "status",
            "order_items",
            "transaction_id",
            "created_at",
            "updated_at",
        ]
