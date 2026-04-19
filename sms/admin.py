from django.contrib import admin

from .models import SMSSendHistory, SMSSetting


@admin.register(SMSSetting)
class SMSSettingAdmin(admin.ModelAdmin):
    list_display = ("sms_credit", "sms_enabled")



@admin.register(SMSSendHistory)
class SMSSendHistoryAdmin(admin.ModelAdmin):
    list_display = ("receiver_number", "credits_used", "sent_at", "status")
    list_filter = ("sent_at", "status")
    search_fields = ("receiver_number",)
