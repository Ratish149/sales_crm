from rest_framework import serializers

from .models import OurClient


class OurClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = OurClient
        fields = "__all__"
