from rest_framework import serializers

from .models import Invoice, InvoiceItem


class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = [
            "id",
            "product",
            "variant",
            "name",
            "quantity",
            "rate",
            "amount",
        ]

    def validate(self, attrs):
        quantity = attrs.get("quantity", 0)
        rate = attrs.get("rate", 0)
        attrs["amount"] = quantity * rate
        return attrs


class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True)

    class Meta:
        model = Invoice
        fields = [
            "id",
            "status",
            "customer",
            "bill_from_name",
            "bill_from_address",
            "bill_from_email",
            "bill_from_phone",
            "bill_from_vat",
            "bill_to_name",
            "bill_to_address",
            "bill_to_email",
            "bill_to_phone",
            "bill_to_vat",
            "invoice_number",
            "invoice_date",
            "due_date",
            "currency",
            "logo",
            "discount",
            "discount_type",
            "vat",
            "total_amount",
            "additional_notes",
            "payment_terms",
            "bank_name",
            "account_name",
            "account_number",
            "signature",
            "created_at",
            "updated_at",
            "items",
        ]

    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        invoice = Invoice.objects.create(**validated_data)

        subtotal = 0
        for item_data in items_data:
            quantity = item_data.get("quantity", 0)
            rate = item_data.get("rate", 0)
            amount = quantity * rate
            item_data["amount"] = amount
            subtotal += amount
            InvoiceItem.objects.create(invoice=invoice, **item_data)

        discount = validated_data.get("discount", 0)
        discount_type = validated_data.get("discount_type", "Percentage")

        if discount_type == "Percentage":
            discount_amount = subtotal * (discount / 100)
        else:
            discount_amount = discount

        vat_rate = validated_data.get("vat", 0)

        taxable_amount = subtotal - discount_amount
        vat_amount = taxable_amount * (vat_rate / 100)
        total_amount = taxable_amount + vat_amount

        invoice.total_amount = total_amount
        invoice.save()

        return invoice

    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if items_data is not None:
            instance.items.all().delete()
            subtotal = 0
            for item_data in items_data:
                quantity = item_data.get("quantity", 0)
                rate = item_data.get("rate", 0)
                amount = quantity * rate
                item_data["amount"] = amount
                subtotal += amount
                InvoiceItem.objects.create(invoice=instance, **item_data)

            discount = instance.discount
            discount_type = instance.discount_type

            if discount_type == "Percentage":
                discount_amount = subtotal * (discount / 100)
            else:
                discount_amount = discount

            vat_rate = instance.vat

            taxable_amount = subtotal - discount_amount
            vat_amount = taxable_amount * (vat_rate / 100)
            total_amount = taxable_amount + vat_amount

            instance.total_amount = total_amount
            instance.save()

        return instance
