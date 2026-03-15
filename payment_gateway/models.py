from django.db import models

# Create your models here.


class Payment(models.Model):
    CHOICES = (
        ("esewa", "Esewa"),
        ("khalti", "Khalti"),
    )
    payment_type = models.CharField(max_length=10, choices=CHOICES, unique=True)
    secret_key = models.CharField(max_length=255, null=True, blank=True)
    merchant_code = models.CharField(max_length=255, null=True, blank=True)
    is_enabled = models.BooleanField(default=False)

    def __str__(self):
        return self.payment_type


class PaymentHistory(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("received", "Received"),
    )
    PAYMENT_CHOICES = (
        ("esewa", "Esewa"),
        ("khalti", "Khalti"),
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
        return f"{self.payment_type} - {self.pay_amount} ({self.status})"
