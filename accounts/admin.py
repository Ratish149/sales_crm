from .models import CustomUser
from django_tenants.utils import tenant_context, get_tenant_model
from django.db import connection
from django.utils.decorators import method_decorator
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, get_object_or_404
from django.urls import path, reverse
from django.http import HttpResponseRedirect
from django.contrib import admin
from .models import CustomUser, StoreProfile, Invitation
# from unfold.admin import ModelAdmin
# Register your models here.


# @admin.register(CustomUser)
# class CustomUserAdmin(admin.ModelAdmin):
#     list_display = ('email', 'role', 'is_staff')


@admin.register(StoreProfile)
class StoreProfileAdmin(admin.ModelAdmin):
    list_display = ('store_name', 'store_address', 'store_number')


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ('email', 'store', 'role', 'accepted', 'created_at')



class MultiTenantCustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name',
                    'last_name', 'is_active', 'get_tenant_info')
    list_filter = ('is_active', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email', 'first_name', 'last_name')

    def get_tenant_info(self, obj):
        """Get tenant information for the user"""
        try:
            # Get all tenants and check which ones this user belongs to
            Tenant = get_tenant_model()
            user_tenants = []

            for tenant in Tenant.objects.exclude(schema_name='public'):
                with tenant_context(tenant):
                    if CustomUser.objects.filter(id=obj.id).exists():
                        user_tenants.append(tenant.domain_url)

            return ', '.join(user_tenants) if user_tenants else 'No tenants'
        except:
            return 'Error loading tenant info'

    get_tenant_info.short_description = 'Tenant Domains'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:user_id>/manage-tenant-data/',
                self.admin_site.admin_view(self.manage_tenant_data_view),
                name='accounts_customuser_manage_tenant_data',
            ),
            path(
                '<int:user_id>/tenant/<str:tenant_domain>/website/',
                self.admin_site.admin_view(self.manage_tenant_websites_view),
                name='accounts_customuser_tenant_websites',
            ),
        ]
        return custom_urls + urls

    def manage_tenant_data_view(self, request, user_id):
        """View to manage tenant-specific data for a user"""
        user = get_object_or_404(CustomUser, id=user_id)
        Tenant = get_tenant_model()

        # Get all tenants where this user exists
        user_tenant_data = []

        for tenant in Tenant.objects.exclude(schema_name='public'):
            with tenant_context(tenant):
                try:
                    tenant_user = CustomUser.objects.filter(id=user.id).first()
                    if tenant_user:
                        # Try to get website data for this user in this tenant
                        websites = []
                        try:
                            from website.models import Website
                            websites = Website.objects.filter(user=tenant_user)
                        except:
                            websites = []

                        user_tenant_data.append({
                            'tenant': tenant,
                            'user': tenant_user,
                            'websites': websites,
                        })
                except:
                    continue

        context = {
            'user': user,
            'user_tenant_data': user_tenant_data,
            'title': f'Manage Tenant Data for {user.username}',
            'opts': self.model._meta,
            'has_change_permission': True,
        }

        return render(request, 'admin/accounts/customuser/manage_tenant_data.html', context)

    def manage_tenant_websites_view(self, request, user_id, tenant_domain):
        """View to manage websites for a user in a specific tenant"""
        user = get_object_or_404(CustomUser, id=user_id)
        Tenant = get_tenant_model()

        try:
            tenant = Tenant.objects.get(domain_url=tenant_domain)
        except Tenant.DoesNotExist:
            return HttpResponseRedirect(reverse('admin:accounts_customuser_changelist'))

        with tenant_context(tenant):
            try:
                from website.models import Website
                tenant_user = CustomUser.objects.get(id=user.id)
                websites = Website.objects.filter(user=tenant_user)

                if request.method == 'POST':
                    # Handle website creation/updates here
                    pass

                context = {
                    'user': user,
                    'tenant': tenant,
                    'websites': websites,
                    'title': f'Websites for {user.username} in {tenant_domain}',
                    'opts': self.model._meta,
                }

                return render(request, 'admin/accounts/customuser/manage_websites.html', context)
            except Exception as e:
                context = {
                    'error': str(e),
                    'user': user,
                    'tenant': tenant,
                }
                return render(request, 'admin/accounts/customuser/error.html', context)


# Register the custom admin
admin.site.register(CustomUser, MultiTenantCustomUserAdmin)
