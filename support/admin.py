from django.contrib import admin

from .models import FAQ, FaqCategory

# Register your models here.

admin.site.register(FaqCategory)
admin.site.register(FAQ)
