# serializers.py
from rest_framework import serializers
from .models import Theme, Page, PageComponent


class ThemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Theme
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "published_version")


class PageComponentSerializer(serializers.ModelSerializer):
    page_slug = serializers.CharField(source="page.slug", read_only=True)

    class Meta:
        model = PageComponent
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "published_version")


class PageSerializer(serializers.ModelSerializer):
    components = PageComponentSerializer(many=True, read_only=True)

    class Meta:
        model = Page
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "published_version")
