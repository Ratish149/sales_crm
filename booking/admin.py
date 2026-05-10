# admin.py
from django.contrib import admin

from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "booking_name",
        "booking_type",
        "customer_name",
        "customer_email",
        "start_date",
        "end_date",
        "total_amount",
        "amount_paid",
        "status",
        "payment_status",
        "created_at",
    ]
    list_filter = [
        "status",
        "payment_status",
        "booking_type",
    ]
    search_fields = [
        "customer_name",
        "customer_email",
        "customer_phone",
        "booking_name",
        "booking_type",
        "transaction_id",
    ]
    readonly_fields = ["id", "created_at", "updated_at"]
    ordering = ["-created_at"]
    date_hierarchy = "created_at"

    fieldsets = (
        (
            "Booking Info",
            {
                "fields": ("id", "booking_type", "booking_name", "status"),
            },
        ),
        (
            "Customer",
            {
                "fields": ("user", "customer_name", "customer_email", "customer_phone"),
            },
        ),
        (
            "Dates & Guests",
            {
                "fields": ("start_date", "end_date", "guests"),
            },
        ),
        (
            "Payment",
            {
                "fields": (
                    "total_amount",
                    "amount_paid",
                    "transaction_id",
                    "payment_status",
                ),
            },
        ),
        (
            "Extra Info",
            {
                "fields": ("notes", "extras"),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
            },
        ),
    )
