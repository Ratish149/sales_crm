import os

import django

# 1️⃣ Set the Django settings module (replace 'config.settings' with your settings module)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sales_crm.settings")

# 2️⃣ Setup Django
django.setup()

# 3️⃣ Now import models
from tenants.models import Client, Domain

# 4️⃣ Create a default tenant
default_tenant = Client.objects.create(
    name="Tenant",
    schema_name="public",  # this is the default schema
)

# 5️⃣ Create a domain for the tenant
domain = Domain.objects.create(
    domain="t0owskkw40w4c0gwwkgoocwc.52.230.96.168.sslip.io",  # your tenant domain
    tenant=default_tenant,
    is_primary=True,
)

print("Default tenant and domain created successfully.")
