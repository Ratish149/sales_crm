import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sales_crm.settings")
django.setup()

from django.core.management import call_command

from tenants.models import Client

schemas = Client.objects.values_list("schema_name", flat=True)

for schema in schemas:
    print("Migrating:", schema)
    try:
        call_command("migrate_schemas", schema_name=schema)
    except Exception as e:
        print("FAILED:", schema, e)
