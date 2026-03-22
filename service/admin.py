from django.contrib import admin
from django.db import models
from tinymce.widgets import TinyMCE

from .models import Service

# Register your models here.


class ServiceAdmin(admin.ModelAdmin):
    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == "content":
            return db_field.formfield(widget=TinyMCE())
        return super().formfield_for_dbfield(db_field, **kwargs)


admin.site.register(Service, ServiceAdmin)
