from django.contrib import admin

from .models import NepdoraVideo


@admin.register(NepdoraVideo)
class NepdoraVideoAdmin(admin.ModelAdmin):
    list_display = ("title", "type", "video_url", "created_at", "updated_at")
    list_filter = ("type", "created_at")
    search_fields = ("title",)
    ordering = ("-created_at",)
