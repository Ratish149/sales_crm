from datetime import date, timedelta

from django.conf import settings
from django.db import models
from django.utils.text import slugify
from django_tenants.models import DomainMixin, TenantMixin


class TemplateCategory(models.Model):
    WEBSITE_TYPE = (
        ("ecommerce", "ecommerce"),
        ("service", "service"),
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True, null=True)
    website_type = models.CharField(
        max_length=10, choices=WEBSITE_TYPE, null=True, blank=True
    )

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class TemplateSubCategory(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True, null=True)
    category = models.ForeignKey(
        TemplateCategory, on_delete=models.CASCADE, related_name="subcategories"
    )

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Client(TenantMixin):
    name = models.CharField(max_length=100)
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True
    )
    created_on = models.DateField(auto_now_add=True)
    paid_until = models.DateField(null=True, blank=True)
    pricing_plan = models.ForeignKey(
        "pricing.Pricing",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clients",
    )
    template_image = models.FileField(
        upload_to="template_images", null=True, blank=True
    )
    is_template_account = models.BooleanField(default=False)
    template_category = models.ForeignKey(
        TemplateCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clients",
    )
    template_subcategory = models.ForeignKey(
        TemplateSubCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clients",
    )

    auto_create_schema = True  # Required for automatic schema creation

    def is_subscription_active(self):
        if self.paid_until:
            return date.today() <= self.paid_until
        return False

    def is_plan_active(self):
        """Check if this tenant's plan is still active."""
        if not self.pricing_plan:
            return False
        if self.paid_until is None:
            # lifetime plan or no expiry
            return True
        return self.paid_until >= date.today()

    def extend_subscription(self, plan):
        """Extend subscription based on the plan's duration"""
        duration_days = plan.get_duration_days()

        if duration_days is None:  # lifetime
            self.paid_until = None
        else:
            if self.paid_until and self.paid_until > date.today():
                self.paid_until += timedelta(days=duration_days)
            else:
                self.paid_until = date.today() + timedelta(days=duration_days)
        self.save()

    def __str__(self):
        return f"{self.name} ({self.pricing_plan or 'No Plan'})"


class Domain(DomainMixin):
    pass


class FacebookPageTenantMap(models.Model):
    """Maps a Facebook Page ID to the owning Tenant (Client)."""

    page_name = models.CharField(max_length=255, blank=True, null=True)

    page_id = models.CharField(max_length=255, unique=True, db_index=True)
    tenant = models.ForeignKey(Client, on_delete=models.CASCADE)

    class Meta:
        db_table = "public_facebook_page_map"  # Explicit table name is helpful
