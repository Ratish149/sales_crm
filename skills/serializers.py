from rest_framework import serializers

from .models import Skills


class SkillsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skills
        fields = [
            "id",
            "name",
            "description",
            "created_at",
            "updated_at",
        ]  # explicit, was __all__
        read_only_fields = ["id", "created_at", "updated_at"]
