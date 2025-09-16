from rest_framework import serializers
from .models import Page, PageComponent, Theme


class ThemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Theme
        fields = ["id", "data"]


class PageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Page
        fields = ["id", "title", "slug"]


class PageComponentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PageComponent
        fields = ["id", "component_id",
                  "component_type", "data", "order", "page"]
