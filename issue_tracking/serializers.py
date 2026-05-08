from rest_framework import serializers

from .models import Issue, IssueCategory


class IssueCategorySerializer(serializers.ModelSerializer):
    """Read/write serializer for IssueCategory — exposes only needed fields."""

    class Meta:
        model = IssueCategory
        fields = ["id", "name"]


class IssueSerializer(serializers.ModelSerializer):
    """Write serializer — accepts issue_category as a FK id."""

    class Meta:
        model = Issue
        fields = [
            "id",
            "issue_category",
            "title",
            "description",
            "priority",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class IssueSerializer2(serializers.ModelSerializer):
    """Read serializer — nests full category detail on GET responses."""

    issue_category = IssueCategorySerializer(read_only=True)

    class Meta:
        model = Issue
        fields = [
            "id",
            "issue_category",
            "title",
            "description",
            "priority",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
