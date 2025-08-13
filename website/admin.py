from django.contrib import admin
from .models import Website
# Register your models here.


@admin.register(Website)
class WebsiteAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
