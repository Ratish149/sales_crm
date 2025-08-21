from django.db import models
from django.utils.text import slugify
# Create your models here.


class Page(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)
        super().save(*args, **kwargs)


class PageComponent(models.Model):
    page = models.ForeignKey(
        Page, on_delete=models.CASCADE, related_name='components', null=True, blank=True)
    component_type = models.CharField(max_length=255, null=True, blank=True)
    component_id = models.CharField(max_length=255)
    data = models.JSONField(null=True, blank=True)
    order = models.IntegerField(default=0, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']
        unique_together = ('page', 'component_type')

    def __str__(self):
        return f"{self.component_type} ({self.component_id})"
