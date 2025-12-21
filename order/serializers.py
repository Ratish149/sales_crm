import base64
import os

import requests
import resend
from django.db import connection, models, transaction
from django.template.loader import render_to_string
from rest_framework import serializers

from customer.serializers import CustomerSerializer
from customer.utils import get_customer_from_request
from product.models import Product, ProductVariant
from product.serializers import ProductOnlySerializer, ProductVariantSerializer
from promo_code.models import PromoCode

from .models import Order, OrderItem

resend.api_key = os.getenv("RESEND_API_KEY")


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
            "city",
            "customer_address",
            "shipping_address",
            "delivery_charge",
            "total_amount",
            "status",
            "transaction_id",
            "created_at",
            "updated_at",
            "is_paid",
            "is_manual",
            "promo_code",
            "note",
            "latitude",
            "longitude",
            "payment_type",
            "items",  # for creating/updating
            "order_items",  # for reading back
        ]
        read_only_fields = ["order_number", "created_at", "updated_at"]

    def create(self, validated_data):
        request = self.context.get("request")
        items_data = validated_data.pop("items", [])

        # Try to find a Customer from the request token
        customer = get_customer_from_request(request)
        validated_data["customer"] = customer

        with transaction.atomic():
            order = Order.objects.create(**validated_data)
            created_items = []
            # Now create order items and update stock
            for item_data in items_data:
                product = item_data.get("product")
                variant = item_data.get("variant")
                quantity = item_data["quantity"]

                # Create order item
                order_item = OrderItem.objects.create(order=order, **item_data)
                created_items.append(
                    {
                        "product_name": str(order_item.product or order_item.variant),
                        "quantity": order_item.quantity,
                        "price": order_item.price,
                    }
                )

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
            # send mail to customer using resend
            if order.customer_email:
                self.send_order_email(order, created_items)

            return order

    def send_order_email(self, order, items):
        try:
            # Get current tenant from DB connection
            tenant = getattr(connection, "tenant", None)
            if tenant:
                tenant_name = tenant.name
            else:
                tenant_name = "Nepdora"

            def get_image_base64(url):
                try:
                    response = requests.get(url, timeout=5)
                    return base64.b64encode(response.content).decode()
                except Exception:
                    return None

            logo_b64 = get_image_base64(
                "https://nepdora.baliyoventures.com/static/logo/fulllogo.png"
            )
            fb_b64 = get_image_base64(
                "https://nepdora.baliyoventures.com/static/social/facebook-logo.png"
            )
            ig_b64 = get_image_base64(
                "https://nepdora.baliyoventures.com/static/social/instagram-logo.png"
            )
            attachments = (
                [
                    {"filename": "logo.png", "content": logo_b64, "content_id": "logo"},
                    {
                        "filename": "facebook.png",
                        "content": fb_b64,
                        "content_id": "facebook",
                    },
                    {
                        "filename": "instagram.png",
                        "content": ig_b64,
                        "content_id": "instagram",
                    },
                ]
                if logo_b64
                else []
            )

            # Prepare template context
            context = {
                "customer_name": order.customer_name,
                "order_number": order.order_number,
                "items": items,
                "total_amount": order.total_amount,
                "delivery_charge": order.delivery_charge,
                "tenant_name": tenant_name,
            }

            html_content = render_to_string(
                "order/email/order_confirmation.html", context
            )

            # Use a verified sender email from environment variable
            # Default to a common verified email if not set
            verified_sender = "nepdora@baliyoventures.com"

            # Include tenant name in the "from" name for personalization
            from_email = f"{tenant_name} <{verified_sender}>"

            # Send via Resend
            resend.Emails.send(
                {
                    "from": from_email,
                    "to": order.customer_email,
                    "subject": f"Order Confirmation #{order.order_number}",
                    "html": html_content,
                    "attachments": attachments,
                }
            )
            print(
                f"Order confirmation email sent successfully to {order.customer_email}"
            )

        except Exception as e:
            # Log the error but don't fail the order creation
            print(f"Email sending failed for order {order.order_number}: {e}")
            # Don't raise ValidationError - allow order to be created even if email fails


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
            "city",
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
            "delivery_charge",
            "payment_type",
        ]
