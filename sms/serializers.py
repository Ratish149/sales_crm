from rest_framework import serializers

from nepdora_payment.models import SMSPurchaseHistory
from tenants.serializers import ClientSerializer

from .models import SMSSendHistory, SMSSetting


class SMSSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SMSSetting
        fields = [
            "id",
            "sms_credit",
            "sms_enabled",
            "delivery_sms_enabled",
            "delivery_sms_template",
        ]
        read_only_fields = ["id", "sms_credit"]


class SMSPurchaseHistorySerializer(serializers.ModelSerializer):
    client = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = SMSPurchaseHistory
        fields = [
            "id",
            "amount",
            "price",
            "transaction_id",
            "payment_type",
            "purchased_at",
            "client",
        ]
        read_only_fields = ["purchased_at"]


class SMSPurchaseListSerializer(serializers.ModelSerializer):
    tenant = ClientSerializer(read_only=True)

    class Meta:
        model = SMSPurchaseHistory
        fields = [
            "id",
            "tenant",
            "amount",
            "price",
            "payment_type",
            "transaction_id",
            "purchased_at",
        ]
        read_only_fields = ["purchased_at"]


class SMSSendHistorySerializer(serializers.ModelSerializer):
    # 'to' and 'text' as aliases for convenience if needed, but receiver_number and message are the model fields
    to = serializers.CharField(write_only=True, required=False)
    text = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = SMSSendHistory
        fields = [
            "id",
            "receiver_number",
            "message",
            "credits_used",
            "sent_at",
            "status",
            "response_data",
            "to",
            "text",
        ]
        read_only_fields = ["credits_used", "sent_at", "status", "response_data"]


class SendCustomSMSSerializer(serializers.Serializer):
    order_id = serializers.IntegerField(required=False, allow_null=True)
    phone_number = serializers.CharField(required=False, allow_null=True)
    message = serializers.CharField()


class TenantSMSSettingSerializer(serializers.Serializer):
    tenant = ClientSerializer(read_only=True)
    sms_enabled = serializers.BooleanField()
    sms_credit = serializers.IntegerField()
    delivery_sms_enabled = serializers.BooleanField()
