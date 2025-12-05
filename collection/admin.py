from django.contrib import admin

from .models import Collection, CollectionData


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "created_at", "updated_at"]
    search_fields = ["name", "slug"]
    readonly_fields = ["slug", "default_fields", "created_at", "updated_at"]
    list_filter = ["created_at"]

    fieldsets = (
        ("Basic Information", {"fields": ("name", "slug")}),
        ("Default Fields", {"fields": ("default_fields",), "classes": ("collapse",)}),
        ("Custom Field Definitions", {"fields": ("fields",)}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(CollectionData)
class CollectionDataAdmin(admin.ModelAdmin):
    list_display = ["id", "collection", "created_at", "updated_at"]
    search_fields = ["collection__name"]
    readonly_fields = ["created_at", "updated_at"]
    list_filter = ["collection", "created_at"]

    fieldsets = (
        ("Collection Reference", {"fields": ("collection",)}),
        ("Data", {"fields": ("data",)}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
