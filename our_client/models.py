from django.db import models

# Create your models here.
from sales_crm.utils.s3bucket import PublicMediaStorage


class OurClient(models.Model):
    name = models.CharField(max_length=100, unique=True, null=True, blank=True)
    logo = models.FileField(upload_to="our_client/logo/", storage=PublicMediaStorage())
    url = models.URLField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
