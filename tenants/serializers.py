from rest_framework import serializers

from accounts.serializers import CustomUserSerializer

from .models import Client, Domain, TemplateCategory, TemplateSubCategory


class ClientSerializer(serializers.ModelSerializer):
    owner = CustomUserSerializer(read_only=True)

    class Meta:
        model = Client
        fields = "__all__"


class DomainSerializer(serializers.ModelSerializer):
    tenant = ClientSerializer(read_only=True)

    class Meta:
        model = Domain
        fields = "__all__"


class TemplateCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TemplateCategory
        fields = ["id", "name", "slug"]


class TemplateSubCategorySerializer(serializers.ModelSerializer):
    category = TemplateCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=TemplateCategory.objects.all(), source="category", write_only=True
    )

    class Meta:
        model = TemplateSubCategory
        fields = ["id", "name", "slug", "category", "category_id"]


class TemplateTenantSerializer(serializers.ModelSerializer):
    domains = serializers.SerializerMethodField()
    template_category = TemplateCategorySerializer(read_only=True)
    template_category_id = serializers.PrimaryKeyRelatedField(
        queryset=TemplateCategory.objects.all(),
        source="template_category",
        write_only=True,
    )
    template_subcategory_id = serializers.PrimaryKeyRelatedField(
        queryset=TemplateSubCategory.objects.all(),
        source="template_subcategory",
        write_only=True,
    )
    template_subcategory = TemplateSubCategorySerializer(read_only=True)

    class Meta:
        model = Client
        fields = [
            "id",
            "name",
            "schema_name",
            "owner_id",
            "created_on",
            "paid_until",
            "template_image",
            "is_template_account",
            "template_category",
            "template_category_id",
            "template_subcategory",
            "template_subcategory_id",
            "domains",
        ]

    def get_domains(self, obj):
        domains = Domain.objects.filter(tenant=obj)
        return [domain.domain for domain in domains]

    def update(self, instance, validated_data):
        # Handles updates for write-only fields
        instance.template_category = validated_data.get(
            "template_category", instance.template_category
        )
        instance.template_subcategory = validated_data.get(
            "template_subcategory", instance.template_subcategory
        )

        return super().update(instance, validated_data)
