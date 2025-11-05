from django.db import models
from django.utils.text import slugify


class Template(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class TemplatePage(models.Model):
    template = models.ForeignKey(
        Template, on_delete=models.CASCADE, related_name="pages"
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("template", "title")
        ordering = ["id"]

    def __str__(self):
        return f"{self.template.name} - ({self.title})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


class TemplatePageComponent(models.Model):
    page = models.ForeignKey(
        TemplatePage, on_delete=models.CASCADE, related_name="components"
    )
    component_type = models.CharField(max_length=255, null=True, blank=True)
    component_id = models.CharField(max_length=255)
    data = models.JSONField(null=True, blank=True)  # Component-specific data
    order = models.IntegerField(default=0, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.component_type} ({self.page.title})"
