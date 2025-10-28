from django.contrib import admin

from .models import FAQ, FAQCategory

# Register your models here.

admin.site.register(FAQCategory)
admin.site.register(FAQ)
