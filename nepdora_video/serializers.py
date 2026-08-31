from rest_framework import serializers

from .models import NepdoraVideo


class NepdoraVideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = NepdoraVideo
        fields = [
            "id",
            "title",
            "type",
            "video_url",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_title(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Title cannot be empty.")
        return value.strip()
