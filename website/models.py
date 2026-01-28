from django.db import models
from django.utils.text import slugify
from solo.models import SingletonModel


class SiteConfig(SingletonModel):
    business_name = models.CharField(max_length=255, blank=True, null=True)
    business_details = models.TextField(blank=True, null=True)
    favicon = models.FileField(upload_to="favicon", null=True, blank=True)
    logo = models.FileField(upload_to="logo", null=True, blank=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=255, blank=True, null=True)
    email = models.CharField(max_length=255, blank=True, null=True)
    working_hours = models.CharField(max_length=255, blank=True, null=True)
    instagram_url = models.URLField(null=True, blank=True)
    facebook_url = models.URLField(null=True, blank=True)
    twitter_url = models.URLField(null=True, blank=True)
    linkedin_url = models.URLField(null=True, blank=True)
    youtube_url = models.URLField(null=True, blank=True)
    tiktok_url = models.URLField(null=True, blank=True)


class Theme(models.Model):
    STATUS = (
        ("published", "Published"),
        ("draft", "Draft"),
    )

    status = models.CharField(max_length=10, choices=STATUS, default="draft")
    data = models.JSONField(null=True, blank=True)
    published_version = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="draft_version",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Theme ({self.status})"


class Page(models.Model):
    STATUS = (
        ("published", "Published"),
        ("draft", "Draft"),
    )

    status = models.CharField(max_length=10, choices=STATUS, default="draft")
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True, null=True)
    theme = models.ForeignKey(Theme, on_delete=models.CASCADE, null=True, blank=True)
    published_version = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="draft_version",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("title", "status")

    def __str__(self):
        return f"{self.title} ({self.status})"

    def save(self, *args, **kwargs):
        base_slug = slugify(self.title)
        if self.status == "draft":
            self.slug = f"{base_slug}-draft"
        else:
            self.slug = base_slug
        super().save(*args, **kwargs)


class PageComponent(models.Model):
    STATUS = (
        ("published", "Published"),
        ("draft", "Draft"),
    )

    status = models.CharField(max_length=10, choices=STATUS, default="draft")
    page = models.ForeignKey(
        Page, on_delete=models.CASCADE, related_name="components", null=True, blank=True
    )
    component_type = models.CharField(max_length=255, null=True, blank=True)
    component_id = models.CharField(max_length=255)
    data = models.JSONField(null=True, blank=True)
    order = models.IntegerField(default=0, null=True, blank=True)
    published_version = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="draft_version",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.component_type} ({self.status})"
