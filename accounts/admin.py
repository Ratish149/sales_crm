from django.contrib import admin
from .models import CustomUser, StoreProfile, Invitation
# from unfold.admin import ModelAdmin
# Register your models here.


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('email', 'role', 'is_staff')


@admin.register(StoreProfile)
class StoreProfileAdmin(admin.ModelAdmin):
    list_display = ('store_name', 'store_address', 'store_number')


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ('email', 'store', 'role', 'accepted', 'created_at')
