from django.db import models

# Create your models here.


class Payment(models.Model):
    CHOICES = (
        ("esewa", "Esewa"),
        ("khalti", "Khalti"),
    )
    payment_type = models.CharField(
        max_length=10, choices=CHOICES, null=True, blank=True
    )
    secret_key = models.CharField(max_length=255, null=True, blank=True)
    merchant_code = models.CharField(max_length=255, null=True, blank=True)
    is_enabled = models.BooleanField(default=False)
