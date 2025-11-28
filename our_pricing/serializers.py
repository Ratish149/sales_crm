from rest_framework import serializers

from .models import OurPricing, OurPricingFeature


class OurPricingFeatureSerializer(serializers.ModelSerializer):
    """Serializer for OurPricingFeature model"""

    class Meta:
        model = OurPricingFeature
        fields = [
            "id",
            "feature",
            "order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class OurPricingSerializer(serializers.ModelSerializer):
    """Serializer for OurPricing model with nested features"""

    features = OurPricingFeatureSerializer(many=True, required=False)

    class Meta:
        model = OurPricing
        fields = [
            "id",
            "name",
            "price",
            "description",
            "is_popular",
            "features",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        """Create OurPricing instance with nested features"""
        features_data = validated_data.pop("features", [])
        pricing = OurPricing.objects.create(**validated_data)

        # Create features if provided
        for feature_data in features_data:
            OurPricingFeature.objects.create(pricing=pricing, **feature_data)

        return pricing

    def update(self, instance, validated_data):
        """Update OurPricing instance with nested features"""
        features_data = validated_data.pop("features", None)

        # Update pricing fields
        instance.name = validated_data.get("name", instance.name)
        instance.price = validated_data.get("price", instance.price)
        instance.description = validated_data.get("description", instance.description)
        instance.save()

        # Update features if provided
        if features_data is not None:
            # Delete existing features and create new ones
            instance.features.all().delete()
            for feature_data in features_data:
                OurPricingFeature.objects.create(pricing=instance, **feature_data)

        return instance
