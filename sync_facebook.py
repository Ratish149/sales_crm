#!/usr/bin/env python
import os

import django

# ---------------------------
# Django setup
# ---------------------------
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sales_crm.settings")
django.setup()

# ---------------------------
# Imports
# ---------------------------
from django_tenants.utils import schema_context

from facebook.models import Facebook
from facebook.utils import (
    sync_conversations_from_facebook,
    sync_messages_for_conversation,
)
from tenants.models import FacebookPageTenantMap


# ---------------------------
# Sync function
# ---------------------------
def sync_all_tenants():
    for page_map in FacebookPageTenantMap.objects.all():
        tenant = page_map.tenant
        print(
            f"🔄 Processing tenant: {tenant.schema_name} | Page: {page_map.page_name}"
        )

        # Activate tenant schema
        with schema_context(tenant.schema_name):
            try:
                fb_page = Facebook.objects.get(
                    page_id=page_map.page_id, is_enabled=True
                )
                sync_conversations_from_facebook(fb_page)
                # Optional: sync messages for all conversations of this page
                for conv in fb_page.conversations.all():
                    sync_messages_for_conversation(conv)
            except Facebook.DoesNotExist:
                print(f"⚠️ Facebook page not found in tenant {tenant.schema_name}")
                continue

    print("✅ All tenants synced.")


# ---------------------------
# Entry point
# ---------------------------
if __name__ == "__main__":
    sync_all_tenants()
