from django.db import models
from django.utils.text import slugify

from sales_crm.utils.file_size_validator import file_size

# Create your models here.


class PortfolioCategory(models.Model):
    name = models.CharField(max_length=255)
    slug = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Portfolio(models.Model):
    title = models.CharField(max_length=255)
    slug = models.CharField(max_length=255, null=True, blank=True)
    content = models.TextField()
    thumbnail_image = models.FileField(
        upload_to="portfolio/images/", null=True, blank=True, validators=[file_size]
    )
    thumbnail_image_alt_description = models.CharField(
        max_length=255, blank=True, null=True
    )
    category = models.ForeignKey(
        "PortfolioCategory", related_name="portfolios", on_delete=models.CASCADE
    )
    tags = models.ManyToManyField(
        "PortfolioTags", related_name="portfolios", blank=True
    )
    project_url = models.URLField(null=True, blank=True)
    github_url = models.URLField(null=True, blank=True)
    meta_title = models.CharField(max_length=255, null=True, blank=True)
    meta_description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("title", "slug")

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)
        super().save(*args, **kwargs)


class PortfolioTags(models.Model):
    name = models.CharField(max_length=255)
    slug = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)
