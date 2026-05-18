from django.contrib import admin

from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "start_date",
        "end_date",
        "city",
        "venue_name",
        "organizer_name",
        "is_featured",
    ]
    list_filter = ["is_featured"]
    search_fields = ["title", "organizer_name", "city", "tags"]
    readonly_fields = ["slug"]
    date_hierarchy = "start_date"
    ordering = ["-start_date"]
