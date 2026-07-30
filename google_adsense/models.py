from django.db import models
from solo.models import SingletonModel


class GoogleAdSense(SingletonModel):
    publisher_id = models.CharField(max_length=255, blank=True, null=True)
    autoAds = models.BooleanField(default=True)
    is_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.publisher_id or "Google AdSense"
