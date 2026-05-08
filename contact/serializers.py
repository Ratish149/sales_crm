from rest_framework import serializers

from .models import Contact, NewsLetter


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = "__all__"


class ContactListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ["id", "name", "phone_number", "email", "is_read", "created_at"]


class NewsLetterSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsLetter
        fields = "__all__"

    def validate_email(self, value):
        if NewsLetter.objects.filter(email__iexact=value, is_subscribed=True).exists():
            raise serializers.ValidationError(
                "This email is already subscribed to the newsletter."
            )
        return value


class NewsLetterListSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsLetter
        fields = ["id", "email", "is_subscribed", "is_read", "created_at"]
