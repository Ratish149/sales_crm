# models.py
from django.db import models

from sales_crm.utils.s3bucket import PublicMediaStorage


class Booking(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("cancelled", "Cancelled"),
        ("completed", "Completed"),
    ]
    PAYMENT_STATUS_CHOICES = [
        ("unpaid", "Unpaid"),
        ("partial", "Partial"),
        ("paid", "Paid"),
        ("refunded", "Refunded"),
    ]

    payment_status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES, default="unpaid"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    user = models.ForeignKey(
        "customer.Customer",
        on_delete=models.CASCADE,
        related_name="bookings",
        null=True,
        blank=True,
    )
    booking_type = models.CharField(max_length=100, blank=True, null=True)
    booking_name = models.CharField(max_length=100, blank=True, null=True)
    customer_name = models.CharField(max_length=255, blank=True, null=True)
    customer_email = models.EmailField(blank=True, null=True)
    customer_phone = models.CharField(max_length=32, blank=True, null=True)

    start_date = models.DateTimeField(blank=True, null=True)
    end_date = models.DateTimeField(blank=True, null=True)
    guests = models.PositiveIntegerField(blank=True, null=True)

    total_amount = models.DecimalField(
        max_digits=12, decimal_places=2, blank=True, null=True
    )
    amount_paid = models.DecimalField(
        max_digits=12, decimal_places=2, blank=True, null=True
    )
    transaction_id = models.CharField(max_length=255, blank=True, null=True)

    payment_screenshot = models.FileField(
        storage=PublicMediaStorage(),
        upload_to="bookings/payment_screenshots/",
        blank=True,
        null=True,
        help_text="Upload a screenshot or photo of the payment proof",
    )
    attachment = models.FileField(
        storage=PublicMediaStorage(),
        upload_to="bookings/attachments/",
        blank=True,
        null=True,
        help_text="Any supporting document related to this booking",
    )

    notes = models.TextField(blank=True, null=True)
    extras = models.JSONField(
        blank=True, null=True, help_text="Any additional data specific to the service"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),  # filter by status
            models.Index(fields=["payment_status"]),  # filter by payment_status
            models.Index(fields=["booking_type"]),  # filter by service type
            models.Index(fields=["customer_email"]),  # lookup by email
            models.Index(fields=["start_date"]),  # date range queries
            models.Index(fields=["user"]),  # FK join
            models.Index(
                fields=["status", "payment_status"]
            ),  # combined filter (most common)
            models.Index(fields=["booking_type", "status"]),  # e.g. all confirmed tours
            models.Index(fields=["-created_at"]),
            models.Index(fields=["end_date"]),
            models.Index(fields=["total_amount"]),
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["transaction_id"]),
        ]

    def __str__(self):
        return f"{self.id} — {self.booking_name or 'Booking'} ({self.status})"
