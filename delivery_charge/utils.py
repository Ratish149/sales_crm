import os

import pandas as pd
from django.db import connection

from .models import DeliveryCharge


def import_default_locations(file_path):
    """Import default location names with coverage areas from Excel, updating DB records."""
    if connection.schema_name == "public":
        print(
            "ℹ️ Skipping public schema import (DeliveryCharge is a tenant-specific table)."
        )
        return True

    try:
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return False

        df = pd.read_excel(file_path)

        # Prepare lists and dictionaries for tracking
        excel_locations = []
        json_mapping = {}

        for _, row in df.iterrows():
            # Check for the correct columns
            loc_name_col = (
                "Location Name" if "Location Name" in row else "location_name"
            )
            cov_area_col = (
                "Coverage Area" if "Coverage Area" in row else "coverage_area"
            )

            if loc_name_col not in row:
                print("❌ Error: Required location name column not found in Excel row.")
                return False

            name = str(row[loc_name_col]).strip()
            if not name or name.lower() == "nan":
                continue

            is_default = name.lower() == "default"
            location_name = None if is_default else name

            # Parse coverage area as list of strings
            raw_coverage = str(row.get(cov_area_col, "")).strip()
            if raw_coverage and raw_coverage.lower() != "nan":
                coverage_area = [
                    val.strip() for val in raw_coverage.split(",") if val.strip()
                ]
            else:
                coverage_area = []

            if not is_default:
                excel_locations.append(location_name)
                json_mapping[location_name] = coverage_area

        # Delete database records that are not in the Excel sheet (excluding the default rate)
        deleted_count, _ = (
            DeliveryCharge.objects
            .filter(is_default=False, location_name__isnull=False)
            .exclude(location_name__in=excel_locations)
            .delete()
        )

        created_count = 0
        updated_count = 0

        # Create or update records in the database
        for name, coverage in json_mapping.items():
            charge_obj = DeliveryCharge.objects.filter(
                location_name=name, is_default=False
            ).first()

            if charge_obj:
                # Update coverage area, leaving all cost columns untouched
                charge_obj.coverage_area = coverage
                charge_obj.save(update_fields=["coverage_area"])
                updated_count += 1
            else:
                # Create a new record
                DeliveryCharge.objects.create(
                    location_name=name, is_default=False, coverage_area=coverage
                )
                created_count += 1

        print(
            f"✅ Database Sync Complete: Created {created_count}, Updated {updated_count}, Deleted {deleted_count} locations."
        )
        return True

    except Exception as e:
        print(f"❌ Error importing locations: {e}")
        import traceback

        traceback.print_exc()
        return False
