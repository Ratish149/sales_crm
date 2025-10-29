from rest_framework import serializers

from .models import PromoCode


class PromoCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromoCode
        fields = "__all__"


class PromoCodeValidationSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=10, required=True)

    def validate_code(self, value):
        """Validate that the promo code exists"""
        try:
            promo_code = PromoCode.objects.get(code=value.upper())
        except PromoCode.DoesNotExist:
            raise serializers.ValidationError("Invalid promo code")

        # Check validity and get message
        is_valid, message = promo_code.is_valid()
        if not is_valid:
            raise serializers.ValidationError(message)

        return value


class PromoCodeDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromoCode
        fields = ["id", "code", "discount_percentage", "valid_from", "valid_to"]
