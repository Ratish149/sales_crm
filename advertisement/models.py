from django.db import models

# Create your models here.


class PopUp(models.Model):
    title = models.CharField(max_length=255, blank=True, null=True)
    image = models.FileField(upload_to='banners/', null=True, blank=True)
    disclaimer = models.TextField(blank=True, null=True)
    enabled_fields = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
