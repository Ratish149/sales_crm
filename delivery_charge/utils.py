import pandas as pd

from .models import DeliveryCharge


def import_default_locations(file_path):
    """Import default location names (no cost values), skipping duplicates."""
    try:
        df = pd.read_excel(file_path)

        created_count = 0
        skipped_count = 0

        for _, row in df.iterrows():
            name = str(row["location_name"]).strip()
            is_default = name.lower() == "default"
            location_name = None if is_default else name

            # Skip if already exists (same name or default)
            if DeliveryCharge.objects.filter(
                location_name=location_name, is_default=is_default
            ).exists():
                skipped_count += 1
                continue

            DeliveryCharge.objects.create(
                location_name=location_name,
                is_default=is_default,
            )
            created_count += 1

        print(
            f"✅ Imported {created_count} new locations. Skipped {skipped_count} duplicates."
        )
        return True

    except Exception as e:
        print(f"❌ Error importing locations: {e}")
        return False
