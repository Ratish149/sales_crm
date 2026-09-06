import uuid
from decimal import Decimal

from django.db import models
from django.utils import timezone


class Cart(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        ABANDONED = "abandoned", "Abandoned"
        CONTACTED = "contacted", "Contacted"
        RECOVERED = "recovered", "Recovered"
        CONVERTED = "converted", "Converted"
        EXPIRED = "expired", "Expired"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        "customer.Customer",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="carts",
    )
    contact_name = models.CharField(max_length=120, blank=True)
    contact_phone = models.CharField(max_length=20, blank=True, db_index=True)
    contact_email = models.EmailField(blank=True)
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    last_activity_at = models.DateTimeField(default=timezone.now, db_index=True)
    abandoned_at = models.DateTimeField(null=True, blank=True)
    recovered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "last_activity_at"]),
            models.Index(fields=["contact_phone", "status"]),
        ]

    def __str__(self):
        name_or_phone = self.contact_name or self.contact_phone or "Anonymous"
        return f"Cart {self.id} ({name_or_phone}) - {self.status}"

    @property
    def total_amount(self) -> Decimal:
        return sum(item.total_price for item in self.items.all())

    @property
    def total_items(self) -> int:
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        related_name="items",
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(
        "product.Product",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="cart_items",
    )
    variant = models.ForeignKey(
        "product.ProductVariant",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="cart_items",
    )
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        if self.variant:
            return f"{self.variant} x {self.quantity}"
        if self.product:
            return f"{self.product.name} x {self.quantity}"
        return f"CartItem {self.id} x {self.quantity}"

    @property
    def total_price(self) -> Decimal:
        return Decimal(self.price) * Decimal(self.quantity)
