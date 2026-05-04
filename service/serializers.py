from rest_framework import serializers

from .models import Service, ServiceCategory


class ServiceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = "__all__"


class ServiceCategoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = [
            "name",
            "slug",
            "thumbnail_image",
            "thumbnail_image_alt_description",
            "created_at",
            "updated_at",
        ]


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = "__all__"


class ServiceListSerializer(serializers.ModelSerializer):
    service_category = ServiceCategoryListSerializer()

    class Meta:
        model = Service
        fields = [
            "title",
            "slug",
            "description",
            "thumbnail_image",
            "thumbnail_image_alt_description",
            "service_category",
            "meta_title",
            "meta_description",
            "created_at",
            "updated_at",
        ]


class BulkCreateServiceItemSerializer(serializers.Serializer):
    """Serializer for a single service item inside the bulk create request."""

    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    meta_title = serializers.CharField(required=False, allow_blank=True, default="")
    meta_description = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    service_category_name = serializers.CharField(required=False, allow_blank=True)


class BulkCreateServiceSerializer(serializers.Serializer):
    """Serializer for the bulk service creation request body."""

    services = BulkCreateServiceItemSerializer(many=True, min_length=1)
