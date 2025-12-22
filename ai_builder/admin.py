from django.contrib import admin

from .models import APIKey


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "is_active", "usage_count", "last_used_at")
    list_filter = ("is_active",)
    search_fields = ("key", "name")
