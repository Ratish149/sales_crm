# theme/signals.py
import os

from django.db.models.signals import post_save
from django.dispatch import receiver

from delivery_charge.models import DeliveryCharge
from delivery_charge.utils import import_default_locations

from .models import Page


@receiver(post_save, sender=Page)
def import_default_locations_on_first_page(sender, instance, created, **kwargs):
    if not created:
        return  # only on new page creation

    # check if delivery charges already exist in this tenant
    if DeliveryCharge.objects.exists():
        return  # already imported, skip

    # if not, import
    default_file_path = os.path.join(
        os.path.dirname(__file__), "..", "delivery_charge", "default_locations.xlsx"
    )
    import_default_locations(default_file_path)
