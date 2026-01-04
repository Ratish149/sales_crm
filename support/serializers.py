from rest_framework import serializers

from .models import FAQ, FAQCategory, NepdoraTestimonial, Contact


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


class NepdoraTestimonialSerializer(serializers.ModelSerializer):
    class Meta:
        model = NepdoraTestimonial
        fields = ["id", "name", "designation", "image", "comment"]


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ["id", "name", "email", "phone_number", "message", "created_at", "updated_at"]
    