from rest_framework import serializers


class BlogPromptSerializer(serializers.Serializer):
    """Serializer for the incoming generation request."""
    prompt = serializers.CharField(
        required=True,
        help_text="The topic or detailed instructions for the blog generation."
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
