from decimal import Decimal
from typing import Optional, Union

from django.db import transaction
from django.utils import timezone

from cart.models import Cart, CartItem
from cart.selectors.cart_selector import get_cart_by_id, get_stale_active_carts
from product.models import Product, ProductVariant


def create_cart(
    customer=None,
    contact_name: str = "",
    contact_phone: str = "",
    contact_email: str = "",
) -> Cart:
    """
    Creates or retrieves an active Cart instance.
    If a logged-in customer is provided and already has an active cart, reuse it.
    """
    if customer:
        existing_cart = (
            Cart.objects
            .filter(customer=customer, status=Cart.Status.ACTIVE)
            .order_by("-last_activity_at")
            .first()
        )
        if existing_cart:
            update_fields = []
            if not existing_cart.contact_name:
                name = f"{customer.first_name} {customer.last_name}".strip()
                if name:
                    existing_cart.contact_name = name
                    update_fields.append("contact_name")
            if not existing_cart.contact_phone and customer.phone:
                existing_cart.contact_phone = customer.phone
                update_fields.append("contact_phone")
            if not existing_cart.contact_email and customer.email:
                existing_cart.contact_email = customer.email
                update_fields.append("contact_email")

            if update_fields:
                existing_cart.save(update_fields=update_fields)

            return existing_cart

        if not contact_name:
            contact_name = f"{customer.first_name} {customer.last_name}".strip()
        if not contact_phone and customer.phone:
            contact_phone = customer.phone
        if not contact_email and customer.email:
            contact_email = customer.email

    cart = Cart.objects.create(
        customer=customer,
        contact_name=contact_name,
        contact_phone=contact_phone,
        contact_email=contact_email,
        status=Cart.Status.ACTIVE,
        last_activity_at=timezone.now(),
    )
    return cart


def associate_cart_with_customer(cart: Cart, customer) -> Cart:
    """
    Associates a guest cart with a logged-in customer and fills missing contact details.
    """
    if not cart or not customer:
        return cart

    update_fields = []
    if cart.customer != customer:
        cart.customer = customer
        update_fields.append("customer")

    name = f"{customer.first_name} {customer.last_name}".strip()
    if not cart.contact_name and name:
        cart.contact_name = name
        update_fields.append("contact_name")

    if not cart.contact_phone and customer.phone:
        cart.contact_phone = customer.phone
        update_fields.append("contact_phone")

    if not cart.contact_email and customer.email:
        cart.contact_email = customer.email
        update_fields.append("contact_email")

    if update_fields:
        cart.save(update_fields=update_fields)

    return cart


@transaction.atomic
def add_or_update_cart_item(
    cart: Cart,
    product: Optional[Product] = None,
    variant: Optional[ProductVariant] = None,
    quantity: int = 1,
    price: Optional[Union[Decimal, float]] = None,
) -> CartItem:
    """
    Adds a new item or updates quantity if the product/variant already exists in cart.
    Updates cart's last_activity_at.
    """
    if price is None:
        if variant and variant.price is not None:
            price = variant.price
        elif product and product.price is not None:
            price = product.price
        else:
            price = Decimal("0.00")

    item = None
    if variant:
        item = cart.items.filter(variant=variant).first()
    elif product:
        item = cart.items.filter(product=product, variant__isnull=True).first()

    if item:
        item.quantity = quantity
        item.price = Decimal(str(price))
        item.save()
    else:
        item = CartItem.objects.create(
            cart=cart,
            product=product or (variant.product if variant else None),
            variant=variant,
            quantity=quantity,
            price=Decimal(str(price)),
        )

    cart.last_activity_at = timezone.now()
    cart.save(update_fields=["last_activity_at", "updated_at"])
    return item


@transaction.atomic
def remove_cart_item(cart: Cart, item_id: int) -> bool:
    """
    Removes a CartItem from cart and updates cart's last_activity_at.
    """
    deleted_count, _ = cart.items.filter(pk=item_id).delete()
    if deleted_count > 0:
        cart.last_activity_at = timezone.now()
        cart.save(update_fields=["last_activity_at", "updated_at"])
        return True
    return False


@transaction.atomic
def update_cart_contact(
    cart: Cart,
    contact_name: Optional[str] = None,
    contact_phone: Optional[str] = None,
    contact_email: Optional[str] = None,
) -> Cart:
    """
    Updates contact fields on a cart and bumps last_activity_at.
    """
    update_fields = ["last_activity_at", "updated_at"]
    if contact_name is not None:
        cart.contact_name = contact_name
        update_fields.append("contact_name")
    if contact_phone is not None:
        cart.contact_phone = contact_phone
        update_fields.append("contact_phone")
    if contact_email is not None:
        cart.contact_email = contact_email
        update_fields.append("contact_email")

    cart.last_activity_at = timezone.now()
    cart.save(update_fields=update_fields)
    return cart


@transaction.atomic
def sweep_abandoned_carts(idle_minutes: int = 45) -> int:
    """
    Sweeps active carts that have been untouched for idle_minutes and marks them as ABANDONED.
    Returns the count of carts marked abandoned.
    """
    now = timezone.now()
    stale_carts = get_stale_active_carts(idle_minutes=idle_minutes)
    count = stale_carts.update(
        status=Cart.Status.ABANDONED,
        abandoned_at=now,
        updated_at=now,
    )
    return count


@transaction.atomic
def convert_cart(cart_id: Union[str, Cart]) -> Optional[Cart]:
    """
    Marks a cart as CONVERTED. If it was previously ABANDONED or CONTACTED, sets recovered_at.
    """
    if isinstance(cart_id, Cart):
        cart = cart_id
    else:
        cart = get_cart_by_id(cart_id)

    if not cart:
        return None

    now = timezone.now()
    if cart.status in [Cart.Status.ABANDONED, Cart.Status.CONTACTED]:
        cart.recovered_at = now

    cart.status = Cart.Status.CONVERTED
    cart.save(update_fields=["status", "recovered_at", "updated_at"])
    return cart
