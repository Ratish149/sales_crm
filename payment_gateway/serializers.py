from rest_framework import serializers

from .models import Payment, PaymentHistory


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["id", "payment_type", "secret_key", "merchant_code", "is_enabled"]


class PaymentSmallSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["id", "payment_type", "is_enabled"]  # unchanged


class PaymentHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentHistory
        fields = [
            "id",
            "payment_type",
            "pay_amount",
            "transaction_id",
            "products_purchased",
            "status",
            "additional_info",
            "is_read",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
