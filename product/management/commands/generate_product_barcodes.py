from django.core.management.base import BaseCommand
from django.db import models
from django_tenants.utils import schema_context
from tenants.models import Client
from product.models import Product


class Command(BaseCommand):
    help = "Generates a unique 12-digit barcode for products missing a barcode across all tenant schemas."

    def add_arguments(self, parser):
        parser.add_argument(
            "--schema",
            type=str,
            help="Specify a single schema name to run the barcode generation on (optional).",
        )

    def handle(self, *args, **options):
        single_schema = options.get("schema")

        if single_schema:
            schemas = [single_schema]
        else:
            schemas = list(Client.objects.values_list("schema_name", flat=True))

        total_updated = 0

        for schema in schemas:
            self.stdout.write(f"Processing schema: {schema}")
            try:
                with schema_context(schema):
                    products_without_barcode = Product.objects.filter(
                        models.Q(barcode__isnull=True) | models.Q(barcode="")
                    )
                    count = products_without_barcode.count()
                    if count == 0:
                        self.stdout.write(
                            self.style.SUCCESS(f"  No products missing barcodes in schema '{schema}'.")
                        )
                        continue

                    self.stdout.write(
                        f"  Found {count} product(s) missing barcodes in schema '{schema}'. Generating barcodes..."
                    )
                    updated_in_schema = 0
                    for product in products_without_barcode:
                        if not product.barcode:
                            product.barcode = Product.generate_unique_barcode()
                            product.save(update_fields=["barcode"])
                            updated_in_schema += 1

                    total_updated += updated_in_schema
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  Successfully updated {updated_in_schema} product(s) in schema '{schema}'."
                        )
                    )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"  FAILED processing schema '{schema}': {str(e)}")
                )

        self.stdout.write(
            self.style.SUCCESS(f"\nDone! Generated barcodes for {total_updated} total product(s) across schemas.")
        )
