from django.contrib import admin

from .models import Client, Domain, FacebookPageTenantMap

# from unfold.admin import ModelAdmin


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "is_template_account", "created_on")


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ("domain", "tenant")


@admin.register(FacebookPageTenantMap)
class FacebookPageTenantMapAdmin(admin.ModelAdmin):
    list_display = ("page_name", "page_id", "tenant")
