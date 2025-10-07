from rest_framework import serializers

from .models import Portfolio, PortfolioCategory, PortfolioTags


class PortfolioCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PortfolioCategory
        fields = ["id", "name", "slug", "created_at", "updated_at"]


class PortfolioTagsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortfolioTags
        fields = ["id", "name", "slug", "created_at", "updated_at"]


class PortfolioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Portfolio
        fields = [
            "id",
            "title",
            "slug",
            "content",
            "thumbnail_image",
            "thumbnail_image_alt_description",
            "category",
            "tags",
            "project_url",
            "github_url",
            "meta_title",
            "meta_description",
            "created_at",
            "updated_at",
        ]


class PortfolioListSerializer(PortfolioSerializer):
    category = PortfolioCategorySerializer(read_only=True)
    tags = PortfolioTagsSerializer(many=True, read_only=True)

    class Meta:
        model = Portfolio
        fields = [
            "id",
            "title",
            "slug",
            "thumbnail_image",
            "thumbnail_image_alt_description",
            "category",
            "tags",
            "meta_title",
            "meta_description",
            "created_at",
            "updated_at",
        ]


class PortfolioDetailSerializer(PortfolioSerializer):
    category = PortfolioCategorySerializer(read_only=True)
    tags = PortfolioTagsSerializer(many=True, read_only=True)

    class Meta:
        model = Portfolio
        fields = [
            "id",
            "title",
            "slug",
            "content",
            "thumbnail_image",
            "thumbnail_image_alt_description",
            "category",
            "tags",
            "project_url",
            "github_url",
            "meta_title",
            "meta_description",
            "created_at",
            "updated_at",
        ]
