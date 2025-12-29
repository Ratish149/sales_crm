from django.contrib import admin

from .models import Page, PageComponent, SiteConfig, Theme


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "slug",
        "status",
        "id",
    )


@admin.register(PageComponent)
class PageComponentAdmin(admin.ModelAdmin):
    list_display = (
        "page",
        "component_type",
        "component_id",
        "status",
        "id",
    )


admin.site.register(Theme)
admin.site.register(SiteConfig)
