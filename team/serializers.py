from rest_framework import serializers

from .models import TeamMember, TeamMemberCategory


class TeamMemberCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamMemberCategory
        fields = "__all__"


class TeamMemberSerializer(serializers.ModelSerializer):
    category = TeamMemberCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=TeamMemberCategory.objects.all(),
        source="category",
        write_only=True,
        allow_null=True,
        required=False,
    )

    class Meta:
        model = TeamMember
        fields = [
            "id",
            "order",
            "name",
            "role",
            "phone_number",
            "category",
            "category_id",
            "photo",
            "about",
            "email",
            "facebook",
            "instagram",
            "linkedin",
            "twitter",
            "created_at",
            "updated_at",
        ]
