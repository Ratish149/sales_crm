# shipping/models.py
from django.db import models


class DeliveryCharge(models.Model):
    location_name = models.CharField(max_length=255, unique=True, null=True, blank=True)
    is_default = models.BooleanField(default=False)
    default_cost = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    cost_0_1kg = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    cost_1_2kg = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    cost_2_3kg = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    cost_3_5kg = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    cost_5_10kg = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    cost_above_10kg = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )

    def __str__(self):
        return self.location_name or "Default"
