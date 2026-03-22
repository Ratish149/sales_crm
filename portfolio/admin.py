from django.contrib import admin

from .models import Portfolio
# Register your models here.

class PortfolioAdmin(admin.ModelAdmin):
    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == "content":
            return db_field.formfield(widget=TinyMCE())
        return super().formfield_for_dbfield(db_field, **kwargs)

admin.site.register(Portfolio, PortfolioAdmin)
