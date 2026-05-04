from rest_framework import serializers


class BlogPromptSerializer(serializers.Serializer):
    """Serializer for the incoming blog generation request."""

    prompt = serializers.CharField(
        required=True,
        help_text="The topic or detailed instructions for the blog generation.",
    )
    multiple = serializers.BooleanField(
        required=False,
        default=False,
        help_text="If true, generate multiple blog posts instead of one.",
    )
    count = serializers.IntegerField(
        required=False,
        default=3,
        min_value=1,
        max_value=10,
        help_text="Number of blog posts to generate when multiple=true (1-10).",
    )


class BlogItemSerializer(serializers.Serializer):
    """A single blog item inside a multiple-blog response."""

    title = serializers.CharField()
    content = serializers.CharField()
    time_to_read = serializers.CharField()
    meta_title = serializers.CharField()
    meta_description = serializers.CharField()
    tags = serializers.ListField(child=serializers.CharField())


class BlogResponseSerializer(serializers.Serializer):
    """Serializer for a single blog response from AI."""

    title = serializers.CharField()
    content = serializers.CharField()
    time_to_read = serializers.CharField()
    meta_title = serializers.CharField()
    meta_description = serializers.CharField()
    tags = serializers.ListField(child=serializers.CharField())


class MultipleBlogResponseSerializer(serializers.Serializer):
    """Serializer for a batch of blog responses from AI."""

    blogs = BlogItemSerializer(many=True)


class ServicePromptSerializer(serializers.Serializer):
    """Serializer for the incoming service generation request."""

    prompt = serializers.CharField(required=True)
    multiple = serializers.BooleanField(
        required=False,
        default=False,
        help_text="If true, generate multiple services instead of one.",
    )
    count = serializers.IntegerField(
        required=False,
        default=3,
        min_value=1,
        max_value=10,
        help_text="Number of services to generate when multiple=true (1-10).",
    )


class ServiceItemSerializer(serializers.Serializer):
    """A single service inside a multiple-service response."""

    title = serializers.CharField()
    description = serializers.CharField()
    meta_title = serializers.CharField()
    meta_description = serializers.CharField()


class ServiceResponseSerializer(serializers.Serializer):
    """Serializer for a single service response from AI."""

    title = serializers.CharField()
    description = serializers.CharField()
    meta_title = serializers.CharField()
    meta_description = serializers.CharField()


class MultipleServiceResponseSerializer(serializers.Serializer):
    """Serializer for a batch of service responses from AI."""

    services = ServiceItemSerializer(many=True)


class PortfolioPromptSerializer(serializers.Serializer):
    """Serializer for the incoming portfolio generation request."""

    prompt = serializers.CharField(required=True)
    multiple = serializers.BooleanField(
        required=False,
        default=False,
        help_text="If true, generate multiple portfolio items instead of one.",
    )
    count = serializers.IntegerField(
        required=False,
        default=3,
        min_value=1,
        max_value=10,
        help_text="Number of portfolio items to generate when multiple=true (1-10).",
    )


class PortfolioItemSerializer(serializers.Serializer):
    """A single portfolio item inside a multiple-portfolio response."""

    title = serializers.CharField()
    content = serializers.CharField()
    meta_title = serializers.CharField()
    meta_description = serializers.CharField()
    tags = serializers.ListField(child=serializers.CharField())


class PortfolioResponseSerializer(serializers.Serializer):
    """Serializer for a single portfolio response from AI."""

    title = serializers.CharField()
    content = serializers.CharField()
    meta_title = serializers.CharField()
    meta_description = serializers.CharField()
    tags = serializers.ListField(child=serializers.CharField())


class MultiplePortfolioResponseSerializer(serializers.Serializer):
    """Serializer for a batch of portfolio responses from AI."""

    portfolios = PortfolioItemSerializer(many=True)


class ProductImagePromptSerializer(serializers.Serializer):
    """Serializer for the incoming product generation request from image."""

    image = serializers.FileField(
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
    multiple = serializers.BooleanField(
        required=False,
        default=False,
        help_text="If true, generate multiple testimonials instead of one.",
    )
    count = serializers.IntegerField(
        required=False,
        default=3,
        min_value=1,
        max_value=20,
        help_text="Number of testimonials to generate when multiple=true (1-20).",
    )


class TestimonialItemSerializer(serializers.Serializer):
    """A single testimonial inside a multiple-testimonial response."""

    name = serializers.CharField()
    designation = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    comment = serializers.CharField()
    image = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class TestimonialResponseSerializer(serializers.Serializer):
    """Serializer for a single testimonial response from AI."""

    name = serializers.CharField()
    designation = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    comment = serializers.CharField()
    image = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class MultipleTestimonialResponseSerializer(serializers.Serializer):
    """Serializer for a batch of testimonials from AI."""

    testimonials = TestimonialItemSerializer(many=True)


class FAQPromptSerializer(serializers.Serializer):
    """Serializer for the incoming FAQ generation request."""

    prompt = serializers.CharField(required=True)
    multiple = serializers.BooleanField(
        required=False,
        default=False,
        help_text="If true, generate multiple FAQs instead of one.",
    )
    count = serializers.IntegerField(
        required=False,
        default=5,
        min_value=1,
        max_value=20,
        help_text="Number of FAQs to generate when multiple=true (1-20).",
    )


class FAQItemSerializer(serializers.Serializer):
    """A single FAQ item inside a multiple-FAQ response."""

    question = serializers.CharField()
    answer = serializers.CharField()


class FAQResponseSerializer(serializers.Serializer):
    """Serializer for a single FAQ response from AI."""

    question = serializers.CharField()
    answer = serializers.CharField()


class MultipleFAQResponseSerializer(serializers.Serializer):
    """Serializer for a batch of FAQ responses from AI."""

    faqs = FAQItemSerializer(many=True)
