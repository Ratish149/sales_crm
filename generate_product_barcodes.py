import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sales_crm.settings")
django.setup()

from django.db import models
from django_tenants.utils import schema_context
from tenants.models import Client
from product.models import Product

schemas = Client.objects.values_list("schema_name", flat=True)
total_updated = 0

for schema in schemas:
    print(f"Processing schema: {schema}")
    try:
        with schema_context(schema):
            products_without_barcode = Product.objects.filter(
                models.Q(barcode__isnull=True) | models.Q(barcode="")
            )
            count = products_without_barcode.count()
            if count == 0:
                print(f"  No products missing barcodes in schema '{schema}'.")
                continue

            print(f"  Found {count} product(s) missing barcodes in schema '{schema}'. Generating...")
            updated_count = 0
            for product in products_without_barcode:
                if not product.barcode:
                    product.barcode = Product.generate_unique_barcode()
                    product.save(update_fields=["barcode"])
                    updated_count += 1
            total_updated += updated_count
            print(f"  Successfully updated {updated_count} product(s) in schema '{schema}'.")
    except Exception as e:
        print(f"  FAILED processing schema '{schema}': {e}")

print(f"\nDone! Generated barcodes for {total_updated} total product(s) across all schemas.")
