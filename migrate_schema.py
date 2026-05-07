# migrate_batch.py
from django.core.management import call_command

from tenants.models import Client

schemas = Client.objects.values_list("schema_name", flat=True)

for i, schema in enumerate(schemas):
    print(f"[{i}] Migrating {schema}")
    try:
        call_command("migrate_schemas", schema_name=schema)
    except Exception as e:
        print("FAILED:", schema, e)
