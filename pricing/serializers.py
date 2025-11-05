# pricing/serializers.py
from rest_framework import serializers

from .models import Pricing, PricingFeature


class PricingFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = PricingFeature
        fields = ["id", "feature", "description", "is_available", "order"]


class PricingSerializer(serializers.ModelSerializer):
    features = PricingFeatureSerializer(many=True, read_only=True)

    class Meta:
        model = Pricing
        fields = [
            "id",
            "plan_type",
            "name",
            "tagline",
            "description",
            "price",
            "unit",
            "is_popular",
            "features",
        ]
