from django.db import models


# Create your models here.
class OurPricing(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(null=True, blank=True)
    is_popular = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Our Pricing"
        verbose_name_plural = "Our Pricing"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class OurPricingFeature(models.Model):
    pricing = models.ForeignKey(
        OurPricing, on_delete=models.CASCADE, related_name="features"
    )
    feature = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Our Pricing Feature"
        verbose_name_plural = "Our Pricing Features"
        ordering = ["order"]

    def __str__(self):
        return f"{self.pricing.name} - {self.feature} - {self.order}"
