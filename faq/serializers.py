from rest_framework import serializers

from .models import FAQ, FAQCategory


class FAQCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQCategory
        fields = "__all__"


class FAQSerializer(serializers.ModelSerializer):
    category = FAQCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=FAQCategory.objects.all(),
        source="category",
        write_only=True,
        allow_null=True,
        required=False,
    )

    class Meta:
        model = FAQ
        fields = ["id", "question", "answer", "category", "category_id"]


class BulkCreateFAQItemSerializer(serializers.Serializer):
    """Serializer for a single FAQ item inside the bulk create request."""

    question = serializers.CharField(max_length=500)
    answer = serializers.CharField(max_length=1000)


class BulkCreateFAQSerializer(serializers.Serializer):
    """Serializer for the bulk FAQ creation request body."""

    faqs = BulkCreateFAQItemSerializer(many=True, min_length=1)
