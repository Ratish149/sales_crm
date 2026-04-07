from django.contrib import admin
from django.db import models
from tinymce.widgets import TinyMCE

from .models import Pricing, PricingFeature, UserSubscription

# Register your models here.

admin.site.register(PricingFeature)


class PricingFeatureInline(admin.TabularInline):
    model = PricingFeature


class PricingAdmin(admin.ModelAdmin):
    formfield_overrides = {models.TextField: {"widget": TinyMCE()}}
    inlines = [PricingFeatureInline]


class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "tenant",
        "user",
        "plan",
        "transaction_id",
        "payment_type",
        "amount",
        "started_on",
        "expires_on",
    )


admin.site.register(Pricing, PricingAdmin)
admin.site.register(UserSubscription, UserSubscriptionAdmin)
