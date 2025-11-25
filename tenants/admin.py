from django.contrib import admin
from django.db import connection

from .models import (
    Client,
    Domain,
    FacebookPageTenantMap,
    TemplateCategory,
    TemplateSubCategory,
)

# from unfold.admin import ModelAdmin


@admin.register(TemplateCategory)
class TemplateCategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)


@admin.register(TemplateSubCategory)
class TemplateSubCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "category")


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ["name", "schema_name", "owner", "created_on", "is_template_account"]
    search_fields = ["name", "schema_name", "owner__email"]
    list_filter = ["is_template_account", "created_on"]
    readonly_fields = ["schema_name", "created_on"]

    def get_queryset(self, request):
        """Force query to run in public schema"""
        connection.set_schema_to_public()
        qs = super().get_queryset(request)
        return qs

    def change_view(self, request, object_id, form_url="", extra_context=None):
        """Ensure we're in public schema when viewing a client"""
        connection.set_schema_to_public()
        return super().change_view(request, object_id, form_url, extra_context)

    def add_view(self, request, form_url="", extra_context=None):
        """Ensure we're in public schema when adding a client"""
        connection.set_schema_to_public()
        return super().add_view(request, form_url, extra_context)

    def delete_view(self, request, object_id, extra_context=None):
        """Ensure we're in public schema when deleting a client"""
        connection.set_schema_to_public()
        return super().delete_view(request, object_id, extra_context)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Ensure foreign key lookups use public schema"""
        connection.set_schema_to_public()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ("domain", "tenant")


@admin.register(FacebookPageTenantMap)
class FacebookPageTenantMapAdmin(admin.ModelAdmin):
    list_display = ("page_name", "page_id", "tenant")
