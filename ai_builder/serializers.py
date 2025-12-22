from rest_framework import serializers

from .models import APIKey


class APIKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = APIKey
        fields = ["id", "key", "name", "is_active", "usage_count", "last_used_at"]
        read_only_fields = ["usage_count", "last_used_at"]
