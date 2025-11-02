from django.db import models
from solo.models import SingletonModel


# Create your models here.
class Facebook(SingletonModel):
    user_token = models.TextField(blank=True, null=True)
    app_id = models.CharField(max_length=255, blank=True, null=True)
    app_secret = models.CharField(max_length=255, blank=True, null=True)
    page_id = models.CharField(max_length=255, blank=True, null=True)
    page_access_token = models.TextField(blank=True, null=True)
    page_name = models.CharField(max_length=255, blank=True, null=True)
    is_enabled = models.BooleanField(default=False)

    def __str__(self):
        return "Facebook"
