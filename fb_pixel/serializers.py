from rest_framework import serializers

from .models import FBPixel, MetaCommerce


class FBPixelSerializer(serializers.ModelSerializer):
    class Meta:
        model = FBPixel
        fields = "__all__"


class MetaCommerceSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetaCommerce
        fields = "__all__"

