from rest_framework import serializers

from .models import Template, TemplatePage, TemplatePageComponent, TemplateTheme


class TemplatePageComponentSerializer(serializers.ModelSerializer):
    page = serializers.PrimaryKeyRelatedField(read_only=True)
    template = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = TemplatePageComponent
        fields = [
            "id",
            "page",
            "template",
            "component_type",
            "component_id",
            "data",
            "order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("page", "template")


class TemplatePageSerializer(serializers.ModelSerializer):
    components = TemplatePageComponentSerializer(many=True, read_only=True)

    class Meta:
        model = TemplatePage
        fields = [
            "id",
            "template",
            "title",
            "slug",
            "components",
            "created_at",
            "updated_at",
        ]


class TemplateSerializer(serializers.ModelSerializer):
    pages = TemplatePageSerializer(many=True, read_only=True)

    class Meta:
        model = Template
        fields = [
            "id",
            "name",
            "slug",
            "pages",
            "created_at",
            "updated_at",
        ]


class TemplateThemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemplateTheme
        fields = [
            "id",
            "template",
            "data",
            "created_at",
            "updated_at",
        ]
