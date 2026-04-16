from rest_framework import serializers

from .models import Portfolio, PortfolioCategory, PortfolioImage, PortfolioTags


class PortfolioCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PortfolioCategory
        fields = ["id", "name", "slug", "created_at", "updated_at"]


class PortfolioTagsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortfolioTags
        fields = ["id", "name", "slug", "created_at", "updated_at"]


class PortfolioImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortfolioImage
        fields = ["id", "image", "alt_description", "created_at", "updated_at"]


class PortfolioSerializer(serializers.ModelSerializer):
    images = serializers.ListField(
        child=serializers.FileField(
            max_length=1000000, allow_empty_file=False, use_url=False
        ),
        write_only=True,
        required=False,
    )

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
            "images",
        ]

    def create(self, validated_data):
        images = validated_data.pop("images", [])
        portfolio = super().create(validated_data)
        for image in images:
            PortfolioImage.objects.create(portfolio=portfolio, image=image)
        return portfolio


class PortfolioListSerializer(PortfolioSerializer):
    category = PortfolioCategorySerializer(read_only=True)
    tags = PortfolioTagsSerializer(many=True, read_only=True)
    images = PortfolioImageSerializer(many=True, read_only=True)

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
            "images",
            "project_url",
            "github_url",
            "meta_title",
            "meta_description",
            "created_at",
            "updated_at",
        ]


class PortfolioDetailSerializer(PortfolioSerializer):
    category = PortfolioCategorySerializer(read_only=True)
    tags = PortfolioTagsSerializer(many=True, read_only=True)
    images = PortfolioImageSerializer(many=True, read_only=True)

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
            "images",
            "project_url",
            "github_url",
            "meta_title",
            "meta_description",
            "created_at",
            "updated_at",
        ]
