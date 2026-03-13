from django.contrib import admin

from .models import NepdoraPayment, TenantCentralPaymentHistory, TenantTransferHistory


@admin.register(NepdoraPayment)
class NepdoraPaymentAdmin(admin.ModelAdmin):
    list_display = ("payment_type",)


@admin.register(TenantCentralPaymentHistory)
class TenantCentralPaymentHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "tenant",
        "payment_type",
        "pay_amount",
        "transaction_id",
        "status",
        "created_at",
    )
    list_filter = ("tenant", "payment_type", "status")
    search_fields = ("transaction_id",)
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"


@admin.register(TenantTransferHistory)
class TenantTransferHistoryAdmin(admin.ModelAdmin):
    list_display = ("tenant", "amount", "transfer_date", "created_at")
    list_filter = ("tenant",)
    search_fields = ("reference_note",)
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "transfer_date"
