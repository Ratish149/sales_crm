import os
from decimal import Decimal

import resend
from django.db import connection, models, transaction
from django.template.loader import render_to_string
from rest_framework import serializers

from customer.models import Customer
from customer.serializers import CustomerSerializer
from customer.utils import get_customer_from_request
from product.models import Product, ProductVariant
from product.serializers import OfferSerializer, ProductOnlySerializer
from promo_code.models import PromoCode
from sms.utils import send_sms_test

from .models import Order, OrderItem, OrderItemImage

resend.api_key = os.getenv("RESEND_API_KEY")


class OrderItemImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItemImage
        fields = ["id", "image", "text"]


class OrderItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(required=False, allow_null=True)
    variant_id = serializers.IntegerField(required=False, allow_null=True)
    uploaded_images = serializers.ListField(
        child=serializers.FileField(allow_empty_file=False, use_url=False),
        required=False,
        write_only=True,
    )
    text = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        write_only=True,
    )

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product_id",
            "variant_id",
            "quantity",
            "price",
            "offer",
            "offer_discount",
            "uploaded_images",
            "text",
        ]

    def validate(self, data):
        product_id = data.get("product_id")
        variant_id = data.get("variant_id")

        try:
            from website.models import SiteConfig

            config = SiteConfig.get_solo()
            use_variant = config.use_product_variant if config else False
        except Exception:
            use_variant = False

        product = None
        variant = None

        if use_variant:
            # If use_product_variant is true, frontend might send variant_id as product_id
            actual_variant_id = variant_id or product_id
            if not actual_variant_id:
                raise serializers.ValidationError(
                    "Either product_id or variant_id must be provided for variant"
                )
            try:
                variant = ProductVariant.objects.get(id=actual_variant_id)
            except ProductVariant.DoesNotExist:
                error_field = "product_id" if not variant_id else "variant_id"
                raise serializers.ValidationError({
                    error_field: [
                        f'Invalid pk "{actual_variant_id}" - object does not exist.'
                    ]
                })
        else:
            if not product_id and not variant_id:
                raise serializers.ValidationError(
                    "Either product_id or variant_id must be provided"
                )

            if product_id:
                try:
                    product = Product.objects.get(id=product_id)
                except Product.DoesNotExist:
                    raise serializers.ValidationError({
                        "product_id": [
                            f'Invalid pk "{product_id}" - object does not exist.'
                        ]
                    })

            if variant_id:
                try:
                    variant = ProductVariant.objects.get(id=variant_id)
                except ProductVariant.DoesNotExist:
                    raise serializers.ValidationError({
                        "variant_id": [
                            f'Invalid pk "{variant_id}" - object does not exist.'
                        ]
                    })

            if product and variant:
                raise serializers.ValidationError(
                    "Cannot specify both product_id and variant_id"
                )

        # Set resolved model instances for create method
        data["product"] = product
        data["variant"] = variant

        # Remove raw ID fields
        data.pop("product_id", None)
        data.pop("variant_id", None)

        # Force price to be the current discounted price
        if variant:
            data["price"] = variant.discounted_price
        elif product:
            data["price"] = product.discounted_price

        return data


class OrderItemDetailSerializer(serializers.ModelSerializer):
    product = serializers.SerializerMethodField()
    offer_details = OfferSerializer(source="offer", read_only=True)
    images = OrderItemImageSerializer(many=True, read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "quantity",
            "price",
            "offer_details",
            "offer_discount",
            "images",
        ]

    def get_product(self, obj):
        if obj.variant:
            product_data = ProductOnlySerializer(
                obj.variant.product, context=self.context
            ).data
            product_data["id"] = obj.variant.id

            options = [v.value for v in obj.variant.option_values.all()]
            if options:
                product_data["name"] = (
                    f"{obj.variant.product.name} ({' '.join(options)})"
                )

            if obj.variant.price is not None:
                product_data["price"] = str(obj.variant.price)

            product_data["discounted_price"] = (
                str(obj.variant.discounted_price)
                if obj.variant.discounted_price is not None
                else None
            )

            if obj.variant.image:
                request = self.context.get("request")
                if request:
                    product_data["thumbnail_image"] = request.build_absolute_uri(
                        obj.variant.image.url
                    )
                else:
                    product_data["thumbnail_image"] = obj.variant.image.url

            return product_data
        elif obj.product:
            return ProductOnlySerializer(obj.product, context=self.context).data
        return None


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(
        many=True, required=False, write_only=True
    )  # Set required=False for updates
    order_items = OrderItemDetailSerializer(source="items", many=True, read_only=True)
    customer_details = CustomerSerializer(source="customer", read_only=True)
    offer_details = OfferSerializer(source="offer", read_only=True)
    promo_code_details = serializers.SerializerMethodField()
    promo_discount = serializers.SerializerMethodField()

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
            "attachment",
            "additional_file",
            "promo_code",
            "promo_code_details",
            "promo_discount",
            "offer",
            "offer_details",
            "offer_discount",
            "note",
            "pos_order",
            "latitude",
            "longitude",
            "payment_type",
            "cash_amount",
            "online_amount",
            "online_payment_type",
            "items",
            "order_items",
        ]
        read_only_fields = [
            "order_number",
            "created_at",
            "updated_at",
        ]

    def get_promo_code_details(self, obj):
        if obj.promo_code:
            return {
                "id": obj.promo_code.id,
                "code": obj.promo_code.code,
                "discount_percentage": obj.promo_code.discount_percentage,
            }
        return None

    def get_promo_discount(self, obj):
        if obj.promo_code:
            subtotal = sum(item.price * item.quantity for item in obj.items.all())
            return subtotal * (obj.promo_code.discount_percentage / Decimal("100.00"))
        return Decimal("0.00")

    def to_internal_value(self, data):
        # If items is a string (e.g. from multipart/form-data), parse it
        if "items" in data and isinstance(data["items"], str):
            import json

            try:
                decoded_items = json.loads(data["items"])
                from django.http import QueryDict

                if isinstance(data, QueryDict):
                    new_data = {}
                    for key in data.keys():
                        if key == "items":
                            new_data["items"] = decoded_items
                        else:
                            vals = data.getlist(key)
                            new_data[key] = vals if len(vals) > 1 else vals[0]
                    data = new_data
                else:
                    if not isinstance(data, dict):
                        data = dict(data)
                    data["items"] = decoded_items
            except (json.JSONDecodeError, TypeError):
                pass
        return super().to_internal_value(data)

    def validate(self, attrs):
        # Determine if this is a creation request or an instance update request
        is_update = self.instance is not None

        # 1. FIX: Fallback to existing total if updating status, instead of defaulting to 0.00
        if "total_amount" in attrs:
            frontend_total = attrs["total_amount"]
        elif is_update:
            frontend_total = self.instance.total_amount
        else:
            frontend_total = Decimal("0.00")

        # 2. Only run full item breakdown validation if items are being modified/passed
        if "items" in attrs or not is_update:
            items = attrs.get("items", [])
            base_subtotal = Decimal("0.00")
            calculated_offer_discount = Decimal("0.00")
            offer_contributions = {}

            for item in items:
                product = item.get("product")
                variant = item.get("variant")
                qty = Decimal(str(item.get("quantity", 0)))

                if variant:
                    base_price = (
                        variant.price
                        if variant.price is not None
                        else (product.final_price if product else Decimal("0.00"))
                    )
                    discounted_price = variant.discounted_price
                    active_offer = variant.active_offer
                elif product:
                    base_price = product.final_price
                    discounted_price = product.discounted_price
                    active_offer = product.active_offer
                else:
                    base_price = Decimal("0.00")
                    discounted_price = Decimal("0.00")
                    active_offer = None

                item_subtotal = base_price * qty
                item_discount = max(
                    Decimal("0.00"), (base_price - discounted_price) * qty
                )
                base_subtotal += item_subtotal
                calculated_offer_discount += item_discount

                if active_offer and item_discount > 0:
                    offer_contributions[active_offer] = (
                        offer_contributions.get(active_offer, Decimal("0.00"))
                        + item_discount
                    )
                    item["offer"] = active_offer
                    item["offer_discount"] = item_discount
                else:
                    item["offer"] = None
                    item["offer_discount"] = Decimal("0.00")

            selected_offer = None
            if offer_contributions:
                selected_offer = max(offer_contributions, key=offer_contributions.get)

            attrs["offer"] = selected_offer
            attrs["offer_discount"] = calculated_offer_discount

        # 3. Validate promo code eligibility criteria if explicitly passed
        if "promo_code" in attrs:
            promo_code = attrs.get("promo_code")
            if promo_code:
                is_valid, msg = promo_code.is_valid()
                if not is_valid:
                    raise serializers.ValidationError({"promo_code": [msg]})

        # 4. Safely apply the preserved total back into validation attributes
        attrs["total_amount"] = frontend_total

        # 5. Validate split payment details
        payment_type = attrs.get("payment_type")
        if not payment_type and is_update:
            payment_type = self.instance.payment_type

        if payment_type == "split":
            cash_amt = attrs.get("cash_amount")
            if cash_amt is None:
                cash_amt = (
                    self.instance.cash_amount
                    if (is_update and "cash_amount" not in attrs)
                    else Decimal("0.00")
                )

            online_amt = attrs.get("online_amount")
            if online_amt is None:
                online_amt = (
                    self.instance.online_amount
                    if (is_update and "online_amount" not in attrs)
                    else Decimal("0.00")
                )

            online_pay_type = attrs.get("online_payment_type")
            if online_pay_type is None:
                online_pay_type = (
                    self.instance.online_payment_type
                    if (is_update and "online_payment_type" not in attrs)
                    else None
                )

            if cash_amt is None:
                cash_amt = Decimal("0.00")
            if online_amt is None:
                online_amt = Decimal("0.00")

            if not online_pay_type:
                raise serializers.ValidationError({
                    "online_payment_type": [
                        "Online payment type must be specified when payment type is split."
                    ]
                })

            total_pay = Decimal(str(cash_amt)) + Decimal(str(online_amt))
            if abs(total_pay - frontend_total) > Decimal("0.01"):
                raise serializers.ValidationError({
                    "non_field_errors": [
                        f"Sum of cash amount ({cash_amt}) and online amount ({online_amt}) must equal total amount ({frontend_total})."
                    ]
                })

        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        items_data = validated_data.pop("items", [])
        customer = get_customer_from_request(request)

        if customer:
            validated_data["customer"] = customer
        elif (
            request
            and request.user
            and request.user.is_authenticated
            and isinstance(request.user, Customer)
        ):
            validated_data["customer"] = request.user

        with transaction.atomic():
            order = Order.objects.create(**validated_data)
            created_items = []

            for i, item_data in enumerate(items_data):
                uploaded_images = item_data.pop("uploaded_images", [])
                item_text = item_data.pop("text", None)

                if not item_text and request and request.data:
                    for tk in [
                        f"items[{i}]text",
                        f"items[{i}][text]",
                        f"items_{i}_text",
                        f"items[{i}].text",
                    ]:
                        if tk in request.data:
                            item_text = request.data.get(tk)
                            if item_text:
                                break

                order_item = OrderItem.objects.create(order=order, **item_data)

                for img in uploaded_images:
                    OrderItemImage.objects.create(
                        order_item=order_item, image=img, text=item_text
                    )

                if request and request.FILES:
                    for key in request.FILES:
                        if (
                            key == f"items[{i}]images"
                            or key == f"items[{i}][images]"
                            or key == f"items[{i}]images[]"
                            or key == f"items_{i}_images"
                            or key == f"items[{i}].images"
                            or key.startswith(f"items_{i}_images_")
                            or key.startswith(f"item_{i}_image_")
                        ):
                            files = request.FILES.getlist(key)
                            for f in files:
                                OrderItemImage.objects.create(
                                    order_item=order_item, image=f, text=item_text
                                )

                created_items.append({
                    "product_name": str(order_item.product or order_item.variant),
                    "quantity": order_item.quantity,
                    "price": order_item.price,
                })

            if order.promo_code:
                PromoCode.objects.filter(id=order.promo_code.id).update(
                    used_count=models.F("used_count") + 1
                )

            if order.customer_email:
                self.send_order_email(order, created_items)

            return order

    def send_order_email(self, order, items):
        try:
            tenant = getattr(connection, "tenant", None)
            if tenant:
                tenant_name = "".join(
                    word.capitalize() for word in tenant.name.replace("-", " ").split()
                )
            else:
                tenant_name = "Nepdora"

            verified_sender = "nepdora@baliyoventures.com"
            from_email = f"{tenant_name} <{verified_sender}>"

            if order.customer_email:
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
                resend.Emails.send({
                    "from": from_email,
                    "to": order.customer_email,
                    "subject": f"Order Confirmation #{order.order_number}",
                    "html": html_content,
                })
                print(
                    f"Order confirmation email sent successfully to {order.customer_email}"
                )

            if (
                tenant
                and hasattr(tenant, "owner")
                and tenant.owner
                and tenant.owner.email
            ):
                admin_email = tenant.owner.email
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
            print(f"Email sending failed for order {order.order_number}: {e}")

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

            products_list = (
                ", ".join([
                    item.product.name if item.product else str(item.variant)
                    for item in order.items.all()
                ])
                or "your items"
            )

            location = (
                order.shipping_address
                or order.city
                or order.customer_address
                or "your address"
            )

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


class AdminOrderSerializer(OrderSerializer):
    items = OrderItemSerializer(many=True, write_only=True)
    order_items = OrderItemDetailSerializer(source="items", many=True, read_only=True)
    customer_details = CustomerSerializer(source="customer", read_only=True)
    offer_details = OfferSerializer(source="offer", read_only=True)
    promo_code_details = serializers.SerializerMethodField()
    promo_discount = serializers.SerializerMethodField()

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
            "attachment",
            "additional_file",
            "promo_code",
            "promo_code_details",
            "promo_discount",
            "offer",
            "offer_details",
            "offer_discount",
            "note",
            "pos_order",
            "latitude",
            "longitude",
            "payment_type",
            "cash_amount",
            "online_amount",
            "online_payment_type",
            "items",
            "order_items",
        ]
        read_only_fields = [
            "order_number",
            "created_at",
            "updated_at",
        ]

    def get_promo_code_details(self, obj):
        if obj.promo_code:
            return {
                "id": obj.promo_code.id,
                "code": obj.promo_code.code,
                "discount_percentage": obj.promo_code.discount_percentage,
            }
        return None

    def get_promo_discount(self, obj):
        if obj.promo_code:
            subtotal = sum(item.price * item.quantity for item in obj.items.all())
            return subtotal * (obj.promo_code.discount_percentage / Decimal("100.00"))
        return Decimal("0.00")

    def create(self, validated_data):
        request = self.context.get("request")
        items_data = validated_data.pop("items", [])

        with transaction.atomic():
            order = Order.objects.create(**validated_data)
            created_items = []
            for i, item_data in enumerate(items_data):
                uploaded_images = item_data.pop("uploaded_images", [])
                item_text = item_data.pop("text", None)

                if not item_text and request and request.data:
                    for tk in [
                        f"items[{i}]text",
                        f"items[{i}][text]",
                        f"items_{i}_text",
                        f"items[{i}].text",
                    ]:
                        if tk in request.data:
                            item_text = request.data.get(tk)
                            if item_text:
                                break

                order_item = OrderItem.objects.create(order=order, **item_data)

                for img in uploaded_images:
                    OrderItemImage.objects.create(
                        order_item=order_item, image=img, text=item_text
                    )

                if request and request.FILES:
                    for key in request.FILES:
                        if (
                            key == f"items[{i}]images"
                            or key == f"items[{i}][images]"
                            or key == f"items[{i}]images[]"
                            or key == f"items_{i}_images"
                            or key == f"items[{i}].images"
                            or key.startswith(f"items_{i}_images_")
                            or key.startswith(f"item_{i}_image_")
                        ):
                            files = request.FILES.getlist(key)
                            for f in files:
                                OrderItemImage.objects.create(
                                    order_item=order_item, image=f, text=item_text
                                )

                created_items.append({
                    "product_name": str(order_item.product or order_item.variant),
                    "quantity": order_item.quantity,
                    "price": order_item.price,
                })

            if order.promo_code:
                PromoCode.objects.filter(id=order.promo_code.id).update(
                    used_count=models.F("used_count") + 1
                )
            if order.customer_email:
                self.send_order_email(order, created_items)

            return order


class OrderListSerializer(serializers.ModelSerializer):
    order_items = OrderItemDetailSerializer(source="items", many=True, read_only=True)
    customer_details = CustomerSerializer(source="customer", read_only=True)
    offer_details = OfferSerializer(source="offer", read_only=True)
    promo_code_details = serializers.SerializerMethodField()
    promo_discount = serializers.SerializerMethodField()

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
            "attachment",
            "additional_file",
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
            "cash_amount",
            "online_amount",
            "online_payment_type",
            "promo_code",
            "promo_code_details",
            "promo_discount",
            "offer",
            "offer_details",
            "offer_discount",
        ]

    def get_promo_code_details(self, obj):
        if obj.promo_code:
            return {
                "id": obj.promo_code.id,
                "code": obj.promo_code.code,
                "discount_percentage": obj.promo_code.discount_percentage,
            }
        return None

    def get_promo_discount(self, obj):
        if obj.promo_code:
            subtotal = sum(item.price * item.quantity for item in obj.items.all())
            return subtotal * (obj.promo_code.discount_percentage / Decimal("100.00"))
        return Decimal("0.00")
