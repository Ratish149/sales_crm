# tenants/signals.py
from datetime import date
from django.db.models.signals import post_save
from django.dispatch import receiver
from tenants.models import Client


@receiver(post_save, sender=Client)
def deactivate_if_expired(sender, instance, **kwargs):
    """
    Automatically deactivate plan if paid_until < today.
    """
    if instance.paid_until and instance.paid_until < date.today():
        if instance.pricing_plan is not None:
            instance.pricing_plan = None
            instance.save(update_fields=["pricing_plan"])
