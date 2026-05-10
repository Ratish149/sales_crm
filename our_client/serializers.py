from rest_framework import serializers

from .models import OurClient


class OurClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = OurClient
        fields = [
            "id",
            "name",
            "logo",
            "url",
            "created_at",
            "updated_at",
        ]  # explicit instead of __all__
