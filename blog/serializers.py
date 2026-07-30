from rest_framework import serializers

from .models import Blog, BlogCategory, Tags


class BlogCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogCategory
        fields = [
            "id",
            "name",
            "slug",
            "thumbnail_image",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "slug", "created_at", "updated_at"]


class BlogCategorySmallSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogCategory
        fields = ["id", "name", "slug", "thumbnail_image"]


class TagsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tags
        fields = "__all__"


class TagsSmallSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tags
        fields = ["id", "name", "slug"]


class BlogSerializer(serializers.ModelSerializer):
    category = BlogCategorySmallSerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=BlogCategory.objects.all(),
        source="category",
        write_only=True,
        required=False,
        allow_null=True,
    )
    tags = TagsSmallSerializer(many=True, read_only=True)
    tag_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )
    tag_names = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )

    class Meta:
        model = Blog
        fields = [
            "id",
            "category",
            "category_id",
            "title",
            "slug",
            "content",
            "tags",
            "tag_ids",
            "tag_names",
            "thumbnail_image",
            "thumbnail_image_alt_description",
            "author",
            "time_to_read",
            "meta_title",
            "meta_description",
            "is_featured",
            "created_at",
            "updated_at",
        ]

    def to_internal_value(self, data):
        if (
            isinstance(data, dict)
            and "category" in data
            and "category_id" not in data
        ):
            category_val = data.get("category")
            if isinstance(category_val, (int, str)) or category_val is None:
                data = data.copy()
                data["category_id"] = category_val
        return super().to_internal_value(data)

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

    def _process_tags(self, tag_ids=None, tag_names=None):
        tag_objects = set()

        if tag_ids:
            existing_tags = Tags.objects.filter(id__in=tag_ids)
            tag_objects.update(existing_tags)

        if tag_names:
            for name in tag_names:
                tag = Tags.objects.filter(name__icontains=name).first()
                if not tag:
                    tag = Tags.objects.create(name=name)
                tag_objects.add(tag)

        return list(tag_objects)

    def create(self, validated_data):
        tag_ids = validated_data.pop("tag_ids", [])
        tag_names = validated_data.pop("tag_names", [])
        blog = Blog.objects.create(**validated_data)

        tags = self._process_tags(tag_ids, tag_names)
        if tags:
            blog.tags.set(tags)
        return blog

    def update(self, instance, validated_data):
        tag_ids = validated_data.pop("tag_ids", None)
        tag_names = validated_data.pop("tag_names", None)
        instance = super().update(instance, validated_data)

        if tag_ids is not None or tag_names is not None:
            tags = self._process_tags(tag_ids or [], tag_names or [])
            instance.tags.set(tags)
        return instance


class BulkCreateBlogItemSerializer(serializers.Serializer):
    """Serializer for a single blog item inside the bulk create request."""

    title = serializers.CharField(max_length=255)
    content = serializers.CharField()
    category = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, default=None
    )
    author = serializers.CharField(
        max_length=255, required=False, allow_null=True, allow_blank=True, default=None
    )
    time_to_read = serializers.CharField(max_length=50, required=False)
    meta_title = serializers.CharField(required=False, allow_blank=True, default="")
    meta_description = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    is_featured = serializers.BooleanField(required=False, default=False)
    tag_names = serializers.ListField(
        child=serializers.CharField(allow_blank=False),
        required=False,
        default=list,
    )


class BulkCreateBlogSerializer(serializers.Serializer):
    """Serializer for the bulk blog creation request body."""

    blogs = BulkCreateBlogItemSerializer(many=True, min_length=1)
