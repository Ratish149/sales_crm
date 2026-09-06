from datetime import timedelta
from typing import Optional

from django.db.models import Prefetch, QuerySet
from django.utils import timezone

from cart.models import Cart, CartItem


def get_optimized_cart_queryset() -> QuerySet[Cart]:
    """
    Returns base optimized queryset for Cart objects, prefetching items with products and variants.
    """
    return (
        Cart.objects
        .select_related("customer")
        .prefetch_related(
            Prefetch(
                "items",
                queryset=CartItem.objects.select_related("product", "variant", "variant__product"),
            )
        )
    )


def get_cart_by_id(cart_id: str) -> Optional[Cart]:
    """
    Retrieves a single Cart object by UUID with optimized relation fetching.
    """
    try:
        return get_optimized_cart_queryset().get(pk=cart_id)
    except (Cart.DoesNotExist, ValueError):
        return None


def get_stale_active_carts(idle_minutes: int = 45) -> QuerySet[Cart]:
    """
    Returns active non-empty carts untouched for specified minutes.
    """
    cutoff = timezone.now() - timedelta(minutes=idle_minutes)
    return (
        Cart.objects
        .filter(
            status=Cart.Status.ACTIVE,
            last_activity_at__lt=cutoff,
            items__isnull=False,
        )
        .distinct()
    )
