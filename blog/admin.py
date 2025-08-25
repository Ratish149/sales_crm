from django.contrib import admin
from .models import Blog, Tags
from tinymce.widgets import TinyMCE
from django.db import models

# Register your models here.
admin.site.register(Tags)


class BlogAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.TextField: {'widget': TinyMCE()}
    }


admin.site.register(Blog, BlogAdmin)
