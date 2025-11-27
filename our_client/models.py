from django.db import models

# Create your models here.


class OurClient(models.Model):
    name = models.CharField(max_length=100, unique=True, null=True, blank=True)
    logo = models.FileField(upload_to="our_client/logo/")
    url = models.URLField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
