from django.contrib import admin
from .models import Blog, Tags
from tinymce.widgets import TinyMCE
from django.db import models

# Register your models here.
admin.site.register(Tags)


class BlogAdmin(admin.ModelAdmin):
    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == "content":
            return db_field.formfield(widget=TinyMCE())
        return super().formfield_for_dbfield(db_field, **kwargs)


admin.site.register(Blog, BlogAdmin)
