from django.core.exceptions import ValidationError
from django.db import models


class NepdoraPayment(models.Model):
    CHOICES = (
        ("esewa", "Esewa"),
        ("khalti", "Khalti"),
    )
    payment_type = models.CharField(max_length=10, choices=CHOICES, unique=True)
    secret_key = models.CharField(max_length=255, null=True, blank=True)
    merchant_code = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.payment_type

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        """Ensure at most one record per payment_type (esewa, khalti)."""
        qs = NepdoraPayment.objects.filter(payment_type=self.payment_type)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.exists():
            raise ValidationError(
                f"A '{self.get_payment_type_display()}' configuration already exists. "
                "Only one entry per payment type is allowed."
            )


class TenantCentralPaymentHistory(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("received", "Received"),
    )
    PAYMENT_CHOICES = (
        ("esewa", "Esewa"),
        ("khalti", "Khalti"),
    )

    tenant = models.ForeignKey(
        "tenants.Client", on_delete=models.CASCADE, related_name="central_payments"
    )
    payment_type = models.CharField(max_length=10, choices=PAYMENT_CHOICES)
    pay_amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=255)
    products_purchased = models.JSONField(default=list, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    additional_info = models.JSONField(default=dict, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.tenant.name} - {self.payment_type} - {self.pay_amount} ({self.status})"


class TenantTransferHistory(models.Model):
    """Records manual transfers made by Nepdora admin to tenants."""

    tenant = models.ForeignKey(
        "tenants.Client",
        on_delete=models.CASCADE,
        related_name="transfer_history",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transfer_date = models.DateTimeField()
    reference_note = models.TextField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.tenant.name} — {self.amount} on {self.transfer_date}"


class SMSPurchaseHistory(models.Model):
    PAYMENT_CHOICES = (
        ("esewa", "Esewa"),
        ("khalti", "Khalti"),
    )
    payment_type = models.CharField(
        max_length=10, choices=PAYMENT_CHOICES, null=True, blank=True
    )
    tenant = models.ForeignKey(
        "tenants.Client", on_delete=models.CASCADE, related_name="sms_purchase_history"
    )
    amount = models.IntegerField(help_text="Number of credits purchased")
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    transaction_id = models.CharField(max_length=255, unique=True)
    purchased_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tenant.name} - {self.amount} credits - {self.transaction_id}"
