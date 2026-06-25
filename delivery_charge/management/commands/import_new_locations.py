import os

from django.conf import settings
from django.core.management.base import BaseCommand

from delivery_charge.utils import import_default_locations


class Command(BaseCommand):
    help = "Imports new delivery locations and coverage areas from Excel file and exports a JSON mapping."

    def handle(self, *args, **options):
        file_path = os.path.join(
            settings.BASE_DIR, "delivery_charge", "default_location.xlsx"
        )
        self.stdout.write(f"Starting import from: {file_path}")
        
        success = import_default_locations(file_path)
        
        if success:
            self.stdout.write(self.style.SUCCESS("Successfully imported delivery locations and coverage areas!"))
        else:
            self.stdout.write(self.style.ERROR("Failed to import delivery locations and coverage areas."))
