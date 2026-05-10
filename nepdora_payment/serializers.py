from rest_framework import serializers

from tenants.models import Client

from .models import NepdoraPayment, TenantCentralPaymentHistory, TenantTransferHistory


class NepdoraPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = NepdoraPayment
        fields = ["id", "payment_type", "secret_key", "merchant_code"]


class TenantCentralPaymentHistorySerializer(serializers.ModelSerializer):
    tenant = serializers.CharField()  # kept exactly as before

    class Meta:
        model = TenantCentralPaymentHistory
        fields = [
            "id",
            "tenant",
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

    def create(self, validated_data):
        tenant_name = validated_data.pop("tenant")
        try:
            tenant = Client.objects.only("id", "name").get(
                name=tenant_name
            )  # only() here saves columns on Client lookup
        except Client.DoesNotExist:
            raise serializers.ValidationError({
                "tenant": f"Tenant with name '{tenant_name}' does not exist."
            })
        except Client.MultipleObjectsReturned:
            raise serializers.ValidationError({
                "tenant": f"Multiple tenants found with name '{tenant_name}'."
            })
        return TenantCentralPaymentHistory.objects.create(
            tenant=tenant, **validated_data
        )


class TenantTransferHistorySerializer(serializers.ModelSerializer):
    tenant = serializers.CharField()  # kept exactly as before

    class Meta:
        model = TenantTransferHistory
        fields = [
            "id",
            "tenant",
            "amount",
            "transfer_date",
            "reference_note",
            "is_read",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        tenant_name = validated_data.pop("tenant")
        try:
            tenant = Client.objects.only("id", "name").get(name=tenant_name)
        except Client.DoesNotExist:
            raise serializers.ValidationError({
                "tenant": f"Tenant with name '{tenant_name}' does not exist."
            })
        except Client.MultipleObjectsReturned:
            raise serializers.ValidationError({
                "tenant": f"Multiple tenants found with name '{tenant_name}'."
            })
        return TenantTransferHistory.objects.create(tenant=tenant, **validated_data)
