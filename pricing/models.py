from django.db import models

# Create your models here.


class Pricing(models.Model):
    PLAN_TYPE = (
        ("free", "Free"),
        ("pro", "pro"),
        ("premium", "Premium"),
    )
    UNIT_CHOICES = [
        ("day", "Day"),
        ("month", "Month"),
        ("year", "Year"),
        ("lifetime", "Lifetime"),
    ]
    plan_type = models.CharField(
        max_length=20,
        choices=PLAN_TYPE,
        default="free",
    )
    name = models.CharField(max_length=255)
    tagline = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(
        max_length=255, null=True, blank=True, choices=UNIT_CHOICES, default="month"
    )
    duration_days = models.PositiveIntegerField(
        null=True, blank=True, help_text="Number of days this plan lasts"
    )
    is_popular = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Automatically calculate duration_days from unit if not set"""
        if self.unit and self.duration_days is None:
            if self.unit == "day":
                self.duration_days = 1
            elif self.unit == "month":
                self.duration_days = 30
            elif self.unit == "year":
                self.duration_days = 365
            elif self.unit == "lifetime":
                self.duration_days = None
        super().save(*args, **kwargs)

    def get_duration_days(self):
        """Return duration days, fallback to 30 if None"""
        if self.duration_days is not None:
            return self.duration_days

    class Meta:
        verbose_name = "Pricing"
        verbose_name_plural = "Pricings"


class PricingFeature(models.Model):
    pricing = models.ForeignKey(
        Pricing, on_delete=models.CASCADE, related_name="features"
    )
    feature = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=1)
    description = models.CharField(max_length=255, null=True, blank=True)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Pricing Feature"
        verbose_name_plural = "Pricing Features"
        ordering = ["order"]

    def __str__(self):
        return f"{self.pricing.name} - {self.feature} - {self.order}"
