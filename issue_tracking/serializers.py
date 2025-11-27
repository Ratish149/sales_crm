from rest_framework import serializers

from .models import Issue, IssueCategory


class IssueCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = IssueCategory
        fields = "__all__"


class IssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Issue
        fields = "__all__"


class IssueSerializer2(serializers.ModelSerializer):
    issue_category = IssueCategorySerializer()

    class Meta:
        model = Issue
        fields = "__all__"
