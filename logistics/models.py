from django.db import models


# Create your models here.
class Logistics(models.Model):
    LOGISTIC_CHOICES = (
        ("Dash", "Dash"),
        ("YDM", "YDM"),
    )
    logistic = models.CharField(
        max_length=10, choices=LOGISTIC_CHOICES, null=True, blank=True
    )
    email = models.EmailField(max_length=255)
    password = models.CharField(max_length=255)
    client_id = models.IntegerField(null=True, blank=True)
    client_secret = models.CharField(max_length=255, null=True, blank=True)
    grant_type = models.CharField(max_length=255, null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_enabled = models.BooleanField(default=False)
    access_token = models.TextField(null=True, blank=True)
    refresh_token = models.TextField(null=True, blank=True)
    api_key = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.logistic