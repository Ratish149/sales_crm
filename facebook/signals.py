# facebook/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django_tenants.utils import (
    get_public_schema_name,
    get_tenant,
    get_tenant_model,
    schema_context,
)

from tenants.models import FacebookPageTenantMap

from .models import Facebook


@receiver(post_save, sender=Facebook)
def create_facebook_page_map(sender, instance, created, **kwargs):
    if not created:
        return  # Only do this when a new Facebook page is created

    try:
        # Get the current tenant
        TenantModel = get_tenant_model()
        tenant = get_tenant()  # gets current tenant automatically
        tenant_name = tenant.schema_name

        # Save mapping in public schema
        with schema_context(get_public_schema_name()):
            # Check if mapping already exists
            if not FacebookPageTenantMap.objects.filter(
                page_id=instance.page_id
            ).exists():
                FacebookPageTenantMap.objects.create(
                    page_id=instance.page_id, tenant=tenant
                )
                print(
                    f"Created FacebookPageTenantMap for page {instance.page_name} -> tenant {tenant_name}"
                )

    except Exception as e:
        print(f"Error creating FacebookPageTenantMap: {e}")
