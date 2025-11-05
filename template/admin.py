from django.contrib import admin

from .models import Template, TemplatePage, TemplatePageComponent

# Register your models here.
admin.site.register(Template)
admin.site.register(TemplatePage)
admin.site.register(TemplatePageComponent)
