from django.contrib import admin
from .models import Client, Domain
# from unfold.admin import ModelAdmin


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'created_on')


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ('domain', 'tenant')
