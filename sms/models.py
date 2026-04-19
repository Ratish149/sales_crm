from django.db import models


class SMSSetting(models.Model):
    """
    Singleton model — only one row (pk=1) is ever allowed.
    Use SMSSetting.load() to retrieve the instance.
    """

    sms_credit = models.IntegerField(default=100)
    sms_enabled = models.BooleanField(default=False)
    delivery_sms_enabled = models.BooleanField(
        default=False,
        help_text="Enable automatic SMS notification when an order is marked as delivered.",
    )
    delivery_sms_template = models.TextField(
        blank=True,
        null=True,
        default="Hi {{name}}, your order containing {{products}} worth Rs. {{total_amount}} has been delivered to {{location}}. Thank you for your purchase!",
        help_text=(
            "Template for delivery SMS. Available placeholders: "
            "{{name}}, {{products}}, {{total_amount}}, {{location}}"
        ),
    )

    class Meta:
        verbose_name = "SMS Setting"
        verbose_name_plural = "SMS Settings"

    def __str__(self):
        return "SMS Settings"

    def save(self, *args, **kwargs):
        """Always save as pk=1 to enforce singleton behaviour."""
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prevent deletion of the singleton row."""
        pass

    @classmethod
    def load(cls):
        """Return the singleton instance, creating it if it doesn't exist."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class SMSSendHistory(models.Model):
    receiver_number = models.CharField(max_length=20)
    message = models.TextField()
    credits_used = models.IntegerField()
    sent_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, null=True, blank=True)
    response_data = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"To {self.receiver_number} - {self.credits_used} credits"
