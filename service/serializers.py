from rest_framework import serializers

from .models import Service, ServiceCategory


class ServiceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "thumbnail_image",
            "thumbnail_image_alt_description",
            "created_at",
            "updated_at",
        ]  # explicit, was __all__
        read_only_fields = ["id", "created_at", "updated_at"]


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
        ]  # unchanged


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = [
            "id",
            "title",
            "slug",
            "description",
            "thumbnail_image",
            "thumbnail_image_alt_description",
            "meta_title",
            "meta_description",
            "service_category",
            "created_at",
            "updated_at",
        ]  # explicit, was __all__
        read_only_fields = ["id", "slug", "created_at", "updated_at"]


class ServiceListSerializer(serializers.ModelSerializer):
    service_category = ServiceCategoryListSerializer(
        read_only=True
    )  # added read_only=True

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
        ]  # unchanged


class BulkCreateServiceItemSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    meta_title = serializers.CharField(required=False, allow_blank=True, default="")
    meta_description = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    service_category_name = serializers.CharField(required=False, allow_blank=True)


class BulkCreateServiceSerializer(serializers.Serializer):
    services = BulkCreateServiceItemSerializer(many=True, min_length=1)
