from django.db import models
from solo.models import SingletonModel


# Create your models here.
class TawkTo(SingletonModel):
    is_enabled = models.BooleanField(default=False)
    widget_id = models.CharField(max_length=255, blank=True, null=True)
    property_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "TawkTo"
