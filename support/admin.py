from django.contrib import admin

from .models import FAQ, FAQCategory, NepdoraTestimonial

# Register your models here.

admin.site.register(FAQCategory)
admin.site.register(FAQ)
admin.site.register(NepdoraTestimonial)
