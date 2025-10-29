from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


# Create your models here.
class PromoCode(models.Model):
    code = models.CharField(max_length=10, unique=True)
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    valid_from = models.DateField(default=timezone.now)
    valid_to = models.DateField()
    max_uses = models.IntegerField(null=True, blank=True)
    used_count = models.IntegerField(default=0, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_valid(self):
        today = timezone.now().date()

        if not self.is_active:
            return False, "Promo code is inactive"

        if today < self.valid_from:
            return False, "Promo code is not yet valid"

        if today > self.valid_to:
            return False, "Promo code has expired"

        if self.max_uses is not None and self.used_count >= self.max_uses:
            return False, "Promo code has reached maximum uses"

        return True, "Valid"

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        # Convert code to uppercase before saving
        self.code = self.code.upper()
        super().save(*args, **kwargs)
