import os

import resend
from django.db import connection, models, transaction
from django.template.loader import render_to_string
from rest_framework import serializers

from customer.models import Customer
from customer.serializers import CustomerSerializer
from customer.utils import get_customer_from_request
from product.models import Product, ProductVariant
from product.serializers import ProductOnlySerializer, ProductVariantSerializer
from promo_code.models import PromoCode
from sms.utils import send_sms_test

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
            "pos_order",
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

        # Handle Customer from token if present
        customer = get_customer_from_request(request)
        if customer:
            validated_data["customer"] = customer
        # or if user is authenticated via other means (e.g. session)
        elif (
            request.user
            and request.user.is_authenticated
            and isinstance(request.user, Customer)
        ):
            validated_data["customer"] = request.user

        with transaction.atomic():
            order = Order.objects.create(**validated_data)
            created_items = []
            # Now create order items and update stock
            for item_data in items_data:
                # Create order item
                order_item = OrderItem.objects.create(order=order, **item_data)
                created_items.append({
                    "product_name": str(order_item.product or order_item.variant),
                    "quantity": order_item.quantity,
                    "price": order_item.price,
                })

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
                tenant_name = "".join(
                    word.capitalize() for word in tenant.name.replace("-", " ").split()
                )
            else:
                tenant_name = "Nepdora"

            # Use a verified sender email from environment variable
            # Default to a common verified email if not set
            verified_sender = "nepdora@baliyoventures.com"

            # Include tenant name in the "from" name for personalization
            from_email = f"{tenant_name} <{verified_sender}>"

            # --- Send to Customer ---
            if order.customer_email:
                # Prepare template context
                context = {
                    "customer_name": order.customer_name,
                    "order_number": order.order_number,
                    "items": items,
                    "total_amount": order.total_amount,
                    "delivery_charge": order.delivery_charge,
                    "tenant_name": tenant_name,
                    "created_at": order.created_at,
                    "track_order_url": f"https://{tenant.schema_name}.nepdora.com/track-order/{order.order_number}"
                    if tenant
                    else f"https://nepdora.com/track-order/{order.order_number}",
                }

                html_content = render_to_string(
                    "order/email/order_confirmation.html", context
                )

                # Send via Resend
                resend.Emails.send({
                    "from": from_email,
                    "to": order.customer_email,
                    "subject": f"Order Confirmation #{order.order_number}",
                    "html": html_content,
                })
                print(
                    f"Order confirmation email sent successfully to {order.customer_email}"
                )

            # --- Send to Admin (Tenant Owner) ---
            if (
                tenant
                and hasattr(tenant, "owner")
                and tenant.owner
                and tenant.owner.email
            ):
                admin_email = tenant.owner.email

                # Prepare template context for admin
                admin_context = {
                    "customer_name": order.customer_name,
                    "customer_email": order.customer_email,
                    "customer_phone": order.customer_phone,
                    "customer_address": order.customer_address,
                    "order_number": order.order_number,
                    "items": items,
                    "total_amount": order.total_amount,
                    "delivery_charge": order.delivery_charge,
                    "tenant_name": tenant_name,
                    "created_at": order.created_at,
                    "track_order_url": f"https://{tenant.schema_name}.nepdora.com/track-order/{order.order_number}"
                    if tenant
                    else f"https://nepdora.com/track-order/{order.order_number}",
                }

                admin_html_content = render_to_string(
                    "order/email/admin_new_order.html", admin_context
                )

                resend.Emails.send({
                    "from": from_email,
                    "to": admin_email,
                    "subject": f"New Order Received #{order.order_number}",
                    "html": admin_html_content,
                })
                print(f"Admin order notification sent successfully to {admin_email}")

        except Exception as e:
            # Log the error but don't fail the order creation
            print(f"Email sending failed for order {order.order_number}: {e}")
            # Don't raise ValidationError - allow order to be created even if email fails

    def send_delivery_sms(self, order, tenant):
        try:
            from sms.models import SMSSetting

            setting = SMSSetting.load()

            if not setting or not setting.sms_enabled:
                return

            if not setting.delivery_sms_enabled:
                return

            if setting.sms_credit <= 0:
                print(
                    f"SMS failed for order delivery {order.order_number}: Insufficient credits."
                )
                return

            # Build product list string
            products_list = (
                ", ".join([
                    item.product.name if item.product else str(item.variant)
                    for item in order.items.select_related("product", "variant").all()
                ])
                or "your items"
            )

            # Resolve location: prefer shipping_address, then city, then customer_address
            location = (
                order.shipping_address
                or order.city
                or order.customer_address
                or "your address"
            )

            # Get template or fall back to a default
            template = setting.delivery_sms_template or (
                "Hi {{name}}, your order containing {{products}} worth "
                "Rs. {{total_amount}} has been delivered to {{location}}. "
                "Thank you for your purchase!"
            )

            message = (
                template
                .replace("{{name}}", order.customer_name or "")
                .replace("{{products}}", products_list)
                .replace("{{total_amount}}", str(order.total_amount))
                .replace("{{location}}", location)
            )

            send_sms_test(to=order.customer_phone, text=message)
        except Exception as e:
            print(f"SMS sending failed for order delivery {order.order_number}: {e}")

    def update(self, instance, validated_data):
        validated_data.pop("items", None)
        old_status = instance.status

        instance = super().update(instance, validated_data)

        new_status = instance.status

        if old_status != "delivered" and new_status == "delivered":
            if instance.customer_phone:
                self.send_delivery_sms(instance, tenant=None)

        return instance


class AdminOrderSerializer(serializers.ModelSerializer):
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
            "pos_order",
            "latitude",
            "longitude",
            "payment_type",
            "items",  # for creating/updating
            "order_items",  # for reading back
        ]
        read_only_fields = ["order_number", "created_at", "updated_at"]

    def create(self, validated_data):
        items_data = validated_data.pop("items", [])

        with transaction.atomic():
            order = Order.objects.create(**validated_data)
            created_items = []
            # Now create order items and update stock
            for item_data in items_data:
                # Create order item
                order_item = OrderItem.objects.create(order=order, **item_data)
                created_items.append({
                    "product_name": str(order_item.product or order_item.variant),
                    "quantity": order_item.quantity,
                    "price": order_item.price,
                })

            # Increment used_count for promo code if one was used
            if order.promo_code:
                PromoCode.objects.filter(id=order.promo_code.id).update(
                    used_count=models.F("used_count") + 1
                )
            # send mail to customer using resend
            if order.customer_email:
                self.send_order_email(order, created_items)

            # send sms notification
            tenant = getattr(connection, "tenant", None)
            if tenant and tenant.sms_enabled and order.customer_phone:
                self.send_order_sms(order, tenant)

            return order

    def send_order_email(self, order, items):
        try:
            # Get current tenant from DB connection
            tenant = getattr(connection, "tenant", None)
            if tenant:
                tenant_name = "".join(
                    word.capitalize() for word in tenant.name.replace("-", " ").split()
                )
            else:
                tenant_name = "Nepdora"

            # Use a verified sender email from environment variable
            # Default to a common verified email if not set
            verified_sender = "nepdora@baliyoventures.com"

            # Include tenant name in the "from" name for personalization
            from_email = f"{tenant_name} <{verified_sender}>"

            # --- Send to Customer ---
            if order.customer_email:
                # Prepare template context
                context = {
                    "customer_name": order.customer_name,
                    "order_number": order.order_number,
                    "items": items,
                    "total_amount": order.total_amount,
                    "delivery_charge": order.delivery_charge,
                    "tenant_name": tenant_name,
                    "created_at": order.created_at,
                    "track_order_url": f"https://{tenant.schema_name}.nepdora.com/track-order/{order.order_number}"
                    if tenant
                    else f"https://nepdora.com/track-order/{order.order_number}",
                }

                html_content = render_to_string(
                    "order/email/order_confirmation.html", context
                )

                # Send via Resend
                resend.Emails.send({
                    "from": from_email,
                    "to": order.customer_email,
                    "subject": f"Order Confirmation #{order.order_number}",
                    "html": html_content,
                })
                print(
                    f"Order confirmation email sent successfully to {order.customer_email}"
                )

            # --- Send to Admin (Tenant Owner) ---
            if (
                tenant
                and hasattr(tenant, "owner")
                and tenant.owner
                and tenant.owner.email
            ):
                admin_email = tenant.owner.email

                # Prepare template context for admin
                admin_context = {
                    "customer_name": order.customer_name,
                    "customer_email": order.customer_email,
                    "customer_phone": order.customer_phone,
                    "customer_address": order.customer_address,
                    "order_number": order.order_number,
                    "items": items,
                    "total_amount": order.total_amount,
                    "delivery_charge": order.delivery_charge,
                    "tenant_name": tenant_name,
                    "created_at": order.created_at,
                    "track_order_url": f"https://{tenant.schema_name}.nepdora.com/track-order/{order.order_number}"
                    if tenant
                    else f"https://nepdora.com/track-order/{order.order_number}",
                }

                admin_html_content = render_to_string(
                    "order/email/admin_new_order.html", admin_context
                )

                resend.Emails.send({
                    "from": from_email,
                    "to": admin_email,
                    "subject": f"New Order Received #{order.order_number}",
                    "html": admin_html_content,
                })
                print(f"Admin order notification sent successfully to {admin_email}")

        except Exception as e:
            # Log the error but don't fail the order creation
            print(f"Email sending failed for order {order.order_number}: {e}")
            # Don't raise ValidationError - allow order to be created even if email fails

    def send_delivery_sms(self, order, tenant):
        try:
            from sms.models import SMSSetting

            setting = SMSSetting.load()

            if not setting or not setting.sms_enabled:
                return

            if not setting.delivery_sms_enabled:
                return

            if setting.sms_credit <= 0:
                print(
                    f"SMS failed for order delivery {order.order_number}: Insufficient credits."
                )
                return

            # Build product list string
            products_list = (
                ", ".join([
                    item.product.name if item.product else str(item.variant)
                    for item in order.items.select_related("product", "variant").all()
                ])
                or "your items"
            )

            # Resolve location: prefer shipping_address, then city, then customer_address
            location = (
                order.shipping_address
                or order.city
                or order.customer_address
                or "your address"
            )

            # Get template or fall back to a default
            template = setting.delivery_sms_template or (
                "Hi {{name}}, your order containing {{products}} worth "
                "Rs. {{total_amount}} has been delivered to {{location}}. "
                "Thank you for your purchase!"
            )

            message = (
                template
                .replace("{{name}}", order.customer_name or "")
                .replace("{{products}}", products_list)
                .replace("{{total_amount}}", str(order.total_amount))
                .replace("{{location}}", location)
            )

            send_sms_test(to=order.customer_phone, text=message)
        except Exception as e:
            print(f"SMS sending failed for order delivery {order.order_number}: {e}")

    def update(self, instance, validated_data):
        validated_data.pop("items", None)
        old_status = instance.status

        instance = super().update(instance, validated_data)

        new_status = instance.status

        if old_status != "delivered" and new_status == "delivered":
            if instance.customer_phone:
                self.send_delivery_sms(instance, tenant=None)

        return instance


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
