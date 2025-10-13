from rest_framework import serializers

from .models import Page, PageComponent, Theme


class ThemeSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    published_version = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Theme
        fields = ["id", "data", "status", "published_version"]


class PageComponentSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    published_version = serializers.PrimaryKeyRelatedField(read_only=True)
    page_slug = serializers.CharField(source="page.slug", read_only=True)

    class Meta:
        model = PageComponent
        fields = [
            "id",
            "component_id",
            "component_type",
            "data",
            "order",
            "status",
            "published_version",
            "page",
            "page_slug",
        ]


class PageSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    published_version = serializers.PrimaryKeyRelatedField(read_only=True)
    components = serializers.SerializerMethodField()

    class Meta:
        model = Page
        fields = ["id", "title", "slug", "status", "published_version", "components"]

    def get_components(self, obj):
        status_param = self.context.get("status", "live")
        qs = obj.components.exclude(component_type__in=["navbar", "footer"])
        if status_param == "preview":
            # merge draft and published, avoid duplicates
            comp_dict = {}
            for comp in qs.order_by("order"):
                key = comp.component_id
                if key not in comp_dict or comp.status == "draft":
                    comp_dict[key] = comp
            return PageComponentSerializer(comp_dict.values(), many=True).data
        return PageComponentSerializer(qs.filter(status="published"), many=True).data
