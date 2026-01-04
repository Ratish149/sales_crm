from django.contrib import admin
from django.db import models
from tinymce.widgets import TinyMCE

from .models import Blog, Tags

# Register your models here.
admin.site.register(Tags)


class BlogAdmin(admin.ModelAdmin):
    formfield_overrides = {models.TextField: {"widget": TinyMCE()}}


admin.site.register(Blog, BlogAdmin)
