from django.db import models
from django.utils.text import slugify

from sales_crm.utils.s3bucket import PublicMediaStorage


class Event(models.Model):
    """
    Generic event model for the custom website builder.
    """

    # Core info
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)

    # Date & Time
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    # Location
    venue_name = models.CharField(max_length=255, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)

    # Media
    thumbnail = models.FileField(
        upload_to="events/thumbnails/",
        storage=PublicMediaStorage(),
        blank=True,
        null=True,
    )
    thumbnail_alt_description = models.CharField(max_length=255, blank=True, null=True)
    # Organizer
    organizer_name = models.CharField(max_length=255, blank=True, null=True)
    organizer_email = models.EmailField(blank=True, null=True)
    organizer_phone = models.CharField(max_length=20, blank=True, null=True)
    organizer_website = models.URLField(blank=True, null=True)

    # SEO / Meta
    meta_title = models.CharField(max_length=255, blank=True, null=True)
    meta_description = models.TextField(blank=True, null=True)

    # Flags
    is_featured = models.BooleanField(default=False)

    # Tags (comma-separated)
    tags = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Comma-separated tags e.g. music, annual, outdoor",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date", "-created_at"]
        indexes = [
            models.Index(fields=["start_date"]),
            models.Index(fields=["is_featured"]),
            models.Index(fields=["slug"]),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)
        super().save(*args, **kwargs)
