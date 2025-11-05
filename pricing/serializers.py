# pricing/serializers.py
from rest_framework import serializers

from .models import Pricing, PricingFeature, UserSubscription


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


class PricingSmallSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pricing
        fields = [
            "id",
            "name",
            "price",
            "unit",
        ]


class UserSubscriptionSerializer(serializers.ModelSerializer):
    plan = PricingSmallSerializer()

    class Meta:
        model = UserSubscription
        fields = [
            "id",
            "tenant",
            "plan",
            "transaction_id",
            "payment_type",
            "amount",
            "started_on",
            "expires_on",
            "created_at",
        ]
