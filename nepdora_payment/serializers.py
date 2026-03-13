from rest_framework import serializers
from .models import NepdoraPayment, TenantCentralPaymentHistory, TenantTransferHistory


class NepdoraPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = NepdoraPayment
        fields = '__all__'


class TenantCentralPaymentHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantCentralPaymentHistory
        fields = '__all__'


class TenantTransferHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantTransferHistory
        fields = '__all__'
