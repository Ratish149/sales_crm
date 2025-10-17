from django.db import models


# Create your models here.
class Youtube(models.Model):
    url = models.URLField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
