from rest_framework import serializers

from .models import Payment, PaymentHistory


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"


class PaymentSmallSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["id", "payment_type", "is_enabled"]


class PaymentHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentHistory
        fields = "__all__"
