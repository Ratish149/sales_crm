from django.contrib import admin

from .models import Payment, PaymentHistory, PaymentQR


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "payment_type", "is_enabled")
    list_filter = ("is_enabled",)
    search_fields = ("payment_type",)


@admin.register(PaymentHistory)
class PaymentHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "payment_type",
        "pay_amount",
        "transaction_id",
        "status",
        "is_read",
        "created_at",
    )
    list_filter = ("payment_type", "status", "is_read", "created_at")
    search_fields = ("transaction_id", "payment_type")
    readonly_fields = ("created_at", "updated_at")


@admin.register(PaymentQR)
class PaymentQRAdmin(admin.ModelAdmin):
    list_display = ("id", "payment_type", "qr", "is_enabled")
    list_filter = ("is_enabled",)
    search_fields = ("payment_type",)
