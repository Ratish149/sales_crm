from django.contrib import admin

from .models import Conversation, Facebook


@admin.register(Facebook)
class FacebookAdmin(admin.ModelAdmin):
    list_display = ("page_name", "page_id", "is_enabled")


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("conversation_id", "page", "get_participants")

    def get_participants(self, obj):
        """Display participant names from JSONField"""
        if not obj.participants:
            return "-"
        names = [p.get("name", "Unknown") for p in obj.participants]
        return ", ".join(names)

    get_participants.short_description = "Participants"
