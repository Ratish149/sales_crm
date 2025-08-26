from rest_framework import serializers
from .models import Order, OrderItem
from product.models import Product


class OrderItemSerializer(serializers.ModelSerializer):
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source='product'
    )

    class Meta:
        model = OrderItem
        fields = ['id', 'product_id', 'quantity', 'price']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, write_only=True)
    order_items = OrderItemSerializer(
        source='items', many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id',
            'order_number',
            'customer_name',
            'customer_email',
            'customer_phone',
            'customer_address',
            'shipping_address',
            'total_amount',
            'status',
            'created_at',
            'updated_at',
            'items',        # for creating/updating
            'order_items',  # for reading back
        ]
        read_only_fields = ['order_number', 'created_at', 'updated_at']

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        order = Order.objects.create(**validated_data)

        # Now create order items
        for item_data in items_data:
            OrderItem.objects.create(order=order, **item_data)

        return order
