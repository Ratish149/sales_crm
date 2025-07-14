from django.contrib import admin
from .models import CustomUser, StoreProfile
# from unfold.admin import ModelAdmin
# Register your models here.


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('email', 'store_name', 'is_staff')


@admin.register(StoreProfile)
class StoreProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'store_address', 'store_number')
