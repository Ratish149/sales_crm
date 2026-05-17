from rest_framework import serializers

from .models import Gallery


class GallerySerializer(serializers.ModelSerializer):
    class Meta:
        model = Gallery
        fields = ["id", "image", "created_at", "updated_at"]


class MultipleGalleryUploadSerializer(serializers.Serializer):
    files = serializers.ListField(
        child=serializers.FileField(allow_empty_file=False), allow_empty=False
    )
