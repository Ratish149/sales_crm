from rest_framework import serializers

from .models import Blog, Tags


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
            "title",
            "slug",
            "content",
            "tags",
            "tag_ids",
            "tag_names",
            "thumbnail_image",
            "thumbnail_image_alt_description",
            "time_to_read",
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
    """Serializer for a single blog item inside the bulk create request.

    `tags` is a list of tag **name strings**. Each name is looked up by
    `tag_names` is a list of tag **name strings**. Each name is looked up by
    case-insensitive match; if it doesn't exist it is created automatically.
    """

    title = serializers.CharField(max_length=255)
    content = serializers.CharField()
    time_to_read = serializers.CharField(max_length=50, required=False)
    meta_title = serializers.CharField(required=False, allow_blank=True, default="")
    meta_description = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    tag_names = serializers.ListField(
        child=serializers.CharField(allow_blank=False),
        required=False,
        default=list,
    )


class BulkCreateBlogSerializer(serializers.Serializer):
    """Serializer for the bulk blog creation request body."""

    blogs = BulkCreateBlogItemSerializer(many=True, min_length=1)
