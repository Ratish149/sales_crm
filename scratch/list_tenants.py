
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sales_crm.settings")
django.setup()

from tenants.models import Client, Domain
from django_tenants.utils import get_public_schema_name

print("Public Schema Name:", get_public_schema_name())
print("\nTenants:")
for client in Client.objects.all():
    print(f"ID: {client.id}, Name: {client.name}, Schema: {client.schema_name}")
    domains = Domain.objects.filter(tenant=client)
    for domain in domains:
        print(f"  - Domain: {domain.domain}, Is Primary: {domain.is_primary}")
