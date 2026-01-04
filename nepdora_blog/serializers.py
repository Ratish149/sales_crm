from rest_framework import serializers

from .models import Blog, BlogCategory, Tags


class BlogCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogCategory
        fields = "__all__"


class BlogCategorySmallSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogCategory
        fields = ["id", "name", "slug"]


class TagsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tags
        fields = "__all__"


class TagsSmallSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tags
        fields = ["id", "name", "slug"]


class BlogSerializer(serializers.ModelSerializer):
    tags = TagsSmallSerializer(many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        required=False,
        source="tags",
        queryset=Tags.objects.all(),
    )
    category = BlogCategorySmallSerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        required=False,
        source="category",
        queryset=BlogCategory.objects.all(),
    )

    class Meta:
        model = Blog
        fields = [
            "id",
            "title",
            "slug",
            "content",
            "tags",
            "thumbnail_image",
            "thumbnail_image_alt_description",
            "time_to_read",
            "tag_ids",
            "category",
            "category_id",
            "meta_title",
            "meta_description",
            "created_at",
            "updated_at",
        ]

    def validate_title(self, value):
        if self.instance:
            if Blog.objects.filter(title=value).exclude(id=self.instance.id).exists():
                raise serializers.ValidationError(
                    "Blog with this title already exists."
                )
        else:
            if Blog.objects.filter(title=value).exists():
                raise serializers.ValidationError(
                    "Blog with this title already exists."
                )
        return value

    def create(self, validated_data):
        tags = validated_data.pop("tags", [])
        blog = Blog.objects.create(**validated_data)
        blog.tags.set(tags)
        return blog

    def update(self, instance, validated_data):
        tags = validated_data.pop("tags", [])
        instance = super().update(instance, validated_data)
        if tags:
            instance.tags.set(tags)
        return instance
