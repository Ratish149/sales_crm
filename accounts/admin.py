from django.contrib import admin

from tenants.models import Client, Domain
from .models import CustomUser, Invitation, StoreProfile, UserActivity


class ClientInline(admin.TabularInline):
    model = Client
    fk_name = "owner"
    extra = 0
    fields = ("name", "schema_name", "get_domains")
    readonly_fields = ("get_domains",)

    @admin.display(description="Domains")
    def get_domains(self, obj):
        return ", ".join(
            Domain.objects.filter(tenant=obj).values_list("domain", flat=True)
        )


class StoreProfileTabularInline(admin.TabularInline):
    model = StoreProfile
    extra = 0


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ("email", "role", "is_staff")
    search_fields = ("email", "first_name", "last_name", "username")
    inlines = [StoreProfileTabularInline, ClientInline]


@admin.register(StoreProfile)
class StoreProfileAdmin(admin.ModelAdmin):
    list_display = ("store_name", "store_address", "store_number")


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ("email", "store", "role", "accepted", "created_at")


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ("user_email", "action", "timestamp")
    list_filter = ("action", "timestamp")
    search_fields = ("user__email", "description")

    @admin.display(description="User Email")
    def user_email(self, obj):
        return obj.user.email if obj.user else "Anonymous"