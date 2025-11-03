from django.contrib import admin

from .models import Conversation, Facebook


@admin.register(Facebook)
class FacebookAdmin(admin.ModelAdmin):
    list_display = ("page_name", "page_id", "is_enabled")


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("conversation_id", "page")
