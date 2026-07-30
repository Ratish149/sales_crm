from django.contrib import admin
from tinymce.widgets import TinyMCE

from .models import Blog, BlogCategory, Tags


@admin.register(BlogCategory)
class BlogCategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "created_at", "updated_at")
    search_fields = ("name", "slug")
    ordering = ("name",)


@admin.register(Tags)
class TagsAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "created_at", "updated_at")
    search_fields = ("name", "slug")
    ordering = ("name",)


@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "category",
        "author",
        "is_featured",
        "created_at",
        "updated_at",
    )
    list_filter = ("is_featured", "category", "created_at")
    search_fields = ("title", "author", "content")
    raw_id_fields = ("category",)
    filter_horizontal = ("tags",)

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == "content":
            return db_field.formfield(widget=TinyMCE())
        return super().formfield_for_dbfield(db_field, **kwargs)
