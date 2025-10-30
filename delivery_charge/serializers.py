from rest_framework import serializers

from .models import DeliveryCharge


class DeliveryChargeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryCharge
        fields = "__all__"


class LocationDeliveryChargeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryCharge
        fields = [
            "id",
            "location_name",
            "default_cost",
            "cost_0_1kg",
            "cost_1_2kg",
            "cost_2_3kg",
            "cost_3_5kg",
            "cost_5_10kg",
            "cost_above_10kg",
        ]
