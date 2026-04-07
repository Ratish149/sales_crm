# pricing/serializers.py
from rest_framework import serializers

from accounts.serializers import CustomUserSerializer

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
    plan = PricingSmallSerializer(read_only=True)
    plan_id = serializers.PrimaryKeyRelatedField(
        queryset=Pricing.objects.all(), source="plan", write_only=True
    )

    class Meta:
        model = UserSubscription
        fields = [
            "id",
            "tenant",
            "user",
            "plan",
            "plan_id",
            "transaction_id",
            "payment_type",
            "amount",
            "started_on",
            "expires_on",
            "created_at",
        ]
        read_only_fields = ["tenant", "user"]


class UserSubscriptionListSerializer(serializers.ModelSerializer):
    plan = PricingSmallSerializer(read_only=True)
    plan_id = serializers.PrimaryKeyRelatedField(
        queryset=Pricing.objects.all(), source="plan", write_only=True
    )
    user = CustomUserSerializer(read_only=True)

    class Meta:
        model = UserSubscription
        fields = [
            "id",
            "tenant",
            "user",
            "plan",
            "plan_id",
            "transaction_id",
            "payment_type",
            "amount",
            "started_on",
            "expires_on",
            "created_at",
        ]
        read_only_fields = ["tenant", "user"]
