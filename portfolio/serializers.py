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
        required=False,
        write_only=True,
    )
    images_data = PortfolioImageSerializer(many=True, read_only=True)

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
            "images_data",
        ]

    def create(self, validated_data):
        images_data = validated_data.pop("images", [])
        portfolio = super().create(validated_data)
        for item in images_data:
            if not isinstance(item, str):  # Ignore strings during creation
                PortfolioImage.objects.create(portfolio=portfolio, image=item)
        return portfolio

    def update(self, instance, validated_data):
        images_data = validated_data.pop("images", [])
        instance = super().update(instance, validated_data)

        existing_images = instance.images.all()
        keep_image_ids = []

        for item in images_data:
            if isinstance(item, str):
                # Sync logic: If it's a URL, find the matching existing image to keep it
                # We use img.image.name because S3 URLs can be dynamic/signed,
                # but the file name (path) remains stable and is part of the URL.
                for img in existing_images:
                    if img.image and img.image.name in item:
                        keep_image_ids.append(img.id)
                        break
            else:
                # If it's a file, it's a new image
                PortfolioImage.objects.create(portfolio=instance, image=item)

        # Delete existing images that were NOT in the provided list of URLs
        existing_images.exclude(id__in=keep_image_ids).delete()

        return instance


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
