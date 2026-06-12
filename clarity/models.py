from django.db import models
from solo.models import SingletonModel


# Create your models here.
class MSClarity(SingletonModel):
    project_id = models.CharField(
        max_length=255, blank=True, null=True, help_text="Microsoft Clarity Project ID"
    )
    is_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "MS Clarity"
