from rest_framework import serializers

from .models import Testimonial


class TestimonialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Testimonial
        fields = "__all__"


class BulkCreateTestimonialItemSerializer(serializers.Serializer):
    """Serializer for a single testimonial item inside the bulk create request."""

    name = serializers.CharField(max_length=255)
    designation = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )
    comment = serializers.CharField()
    base64_image = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class BulkCreateTestimonialSerializer(serializers.Serializer):
    """Serializer for the bulk testimonial creation request body."""

    testimonials = BulkCreateTestimonialItemSerializer(many=True, min_length=1)
