from rest_framework import serializers
from .models import Blog, Tags


class TagsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tags
        fields = '__all__'


class TagsSmallSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tags
        fields = ['id', 'name', 'slug']


class BlogSerializer(serializers.ModelSerializer):
    tags = TagsSmallSerializer(many=True, read_only=True)
    tag_ids = serializers.ListField(child=serializers.IntegerField(
    ), write_only=True, required=False, source='tags')

    class Meta:
        model = Blog
        fields = ['id', 'title', 'slug', 'content', 'tags',
                  'thumbnail_image', 'thumbnail_image_alt_description', 'time_to_read', 'tag_ids', 'meta_title', 'meta_description', 'created_at', 'updated_at',]

    def create(self, validated_data):
        tag_ids = validated_data.pop('tags', [])
        blog = Blog.objects.create(**validated_data)
        blog.tags.set(tag_ids)
        return blog

    def update(self, instance, validated_data):
        tag_ids = validated_data.pop('tags', [])
        instance = super().update(instance, validated_data)
        instance.tags.set(tag_ids)
        return instance
