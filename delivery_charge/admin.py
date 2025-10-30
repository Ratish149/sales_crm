from django.contrib import admin

from .models import DeliveryCharge


# Register your models here.
class DeliveryChargeAdmin(admin.ModelAdmin):
    ordering = ("location_name",)


admin.site.register(DeliveryCharge, DeliveryChargeAdmin)
