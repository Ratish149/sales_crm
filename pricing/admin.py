from django.contrib import admin
from django.db import models
from tinymce.widgets import TinyMCE

from .models import Pricing, PricingFeature

# Register your models here.

admin.site.register(PricingFeature)


class PricingFeatureInline(admin.TabularInline):
    model = PricingFeature


class PricingAdmin(admin.ModelAdmin):
    formfield_overrides = {models.TextField: {"widget": TinyMCE()}}
    inlines = [PricingFeatureInline]


admin.site.register(Pricing, PricingAdmin)
