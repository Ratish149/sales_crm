from django.contrib import admin
from tinymce.widgets import TinyMCE

from .models import Portfolio, PortfolioImage

# Register your models here.


class PortfolioImageInline(admin.TabularInline):
    model = PortfolioImage
    extra = 1


class PortfolioAdmin(admin.ModelAdmin):
    inlines = [PortfolioImageInline]

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == "content":
            return db_field.formfield(widget=TinyMCE())
        return super().formfield_for_dbfield(db_field, **kwargs)


admin.site.register(Portfolio, PortfolioAdmin)
