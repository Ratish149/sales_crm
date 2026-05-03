from rest_framework import serializers


class BlogPromptSerializer(serializers.Serializer):
    """Serializer for the incoming generation request."""

    prompt = serializers.CharField(
        required=True,
        help_text="The topic or detailed instructions for the blog generation.",
    )


class BlogResponseSerializer(serializers.Serializer):
    """Serializer for the structured blog response from AI."""

    title = serializers.CharField()
    content = serializers.CharField()
    time_to_read = serializers.CharField()
    meta_title = serializers.CharField()
    meta_description = serializers.CharField()
    tags = serializers.ListField(child=serializers.CharField())


class ServicePromptSerializer(serializers.Serializer):
    """Serializer for the incoming service generation request."""

    prompt = serializers.CharField(required=True)


class ServiceResponseSerializer(serializers.Serializer):
    """Serializer for the structured service response from AI."""

    title = serializers.CharField()
    description = serializers.CharField()
    meta_title = serializers.CharField()
    meta_description = serializers.CharField()


class PortfolioPromptSerializer(serializers.Serializer):
    """Serializer for the incoming portfolio generation request."""

    prompt = serializers.CharField(required=True)


class PortfolioResponseSerializer(serializers.Serializer):
    """Serializer for the structured portfolio response from AI."""

    title = serializers.CharField()
    content = serializers.CharField()
    meta_title = serializers.CharField()
    meta_description = serializers.CharField()
    tags = serializers.ListField(child=serializers.CharField())


class ProductImagePromptSerializer(serializers.Serializer):
    """Serializer for the incoming product generation request from image."""

    image = serializers.ImageField(
        required=True, help_text="The product image to generate details from."
    )


class ProductResponseSerializer(serializers.Serializer):
    """Serializer for the structured product response from AI."""

    name = serializers.CharField()
    description = serializers.CharField()
    price = serializers.FloatField(required=False, allow_null=True)
    market_price = serializers.FloatField(required=False, allow_null=True)
    weight = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    thumbnail_alt_description = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    meta_title = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    meta_description = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    suggested_category = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )


class TestimonialPromptSerializer(serializers.Serializer):
    """Serializer for the incoming testimonial generation request."""

    prompt = serializers.CharField(required=True)
    generate_image = serializers.BooleanField(
        required=False,
        default=True,
        help_text="Whether to also generate a profile image.",
    )


class TestimonialResponseSerializer(serializers.Serializer):
    """Serializer for the structured testimonial response from AI."""

    name = serializers.CharField()
    designation = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    comment = serializers.CharField()
    image_base64 = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )


class FAQPromptSerializer(serializers.Serializer):
    """Serializer for the incoming FAQ generation request."""

    prompt = serializers.CharField(required=True)


class FAQResponseSerializer(serializers.Serializer):
    """Serializer for the structured FAQ response from AI."""

    question = serializers.CharField()
    answer = serializers.CharField()
