from django.contrib import admin
from django.db import models
from tinymce.widgets import TinyMCE

from .models import Service

# Register your models here.


class ServiceAdmin(admin.ModelAdmin):
    formfield_overrides = {models.TextField: {"widget": TinyMCE()}}


admin.site.register(Service, ServiceAdmin)
