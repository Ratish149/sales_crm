# serializers.py
from rest_framework import serializers

from .models import Page, PageComponent, SiteConfig, Theme


class SiteConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteConfig
        fields = "__all__"


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


class PageListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Page
        fields = ("id", "title", "slug", "status", "theme", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at", "published_version")
