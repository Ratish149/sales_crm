from django.db import models
from django.utils.text import slugify


# Create your models here.
class Service(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    thumbnail_image = models.FileField(
        upload_to="service/thumbnail", null=True, blank=True
    )
    thumbnail_image_alt_description = models.CharField(
        max_length=255, null=True, blank=True
    )
    meta_title = models.CharField(max_length=255, null=True, blank=True)
    meta_description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)
        super().save(*args, **kwargs)
