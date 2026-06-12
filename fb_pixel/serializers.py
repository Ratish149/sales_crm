from rest_framework import serializers

from .models import FBPixel


class FBPixelSerializer(serializers.ModelSerializer):
    class Meta:
        model = FBPixel
        fields = "__all__"
