from rest_framework import serializers

from tenants.models import Client

from .models import NepdoraPayment, TenantCentralPaymentHistory, TenantTransferHistory


class NepdoraPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = NepdoraPayment
        fields = "__all__"


class TenantCentralPaymentHistorySerializer(serializers.ModelSerializer):
    tenant = serializers.CharField()

    class Meta:
        model = TenantCentralPaymentHistory
        fields = "__all__"

    def create(self, validated_data):
        tenant_name = validated_data.pop("tenant")
        try:
            tenant = Client.objects.get(name=tenant_name)
        except Client.DoesNotExist:
            raise serializers.ValidationError(
                {"tenant": f"Tenant with name '{tenant_name}' does not exist."}
            )
        except Client.MultipleObjectsReturned:
            raise serializers.ValidationError(
                {"tenant": f"Multiple tenants found with name '{tenant_name}'."}
            )

        return TenantCentralPaymentHistory.objects.create(
            tenant=tenant, **validated_data
        )


class TenantTransferHistorySerializer(serializers.ModelSerializer):
    tenant = serializers.CharField()

    class Meta:
        model = TenantTransferHistory
        fields = "__all__"

    def create(self, validated_data):
        tenant_name = validated_data.pop("tenant")
        try:
            tenant = Client.objects.get(name=tenant_name)
        except Client.DoesNotExist:
            raise serializers.ValidationError(
                {"tenant": f"Tenant with name '{tenant_name}' does not exist."}
            )
        except Client.MultipleObjectsReturned:
            raise serializers.ValidationError(
                {"tenant": f"Multiple tenants found with name '{tenant_name}'."}
            )

        return TenantTransferHistory.objects.create(tenant=tenant, **validated_data)
