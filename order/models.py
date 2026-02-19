import hashlib

from django.db import models

from product.models import Product
from promo_code.models import PromoCode

# Create your models here.


class Order(models.Model):
    ORDER_STATUS = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("processing", "Processing"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
    ]
    PAYMENT_TYPE = [
        ("cod", "Cash On Delivery"),
        ("khalti", "Khalti"),
        ("esewa", "Esewa"),
    ]
    customer = models.ForeignKey(
        "customer.Customer",
        on_delete=models.CASCADE,
        related_name="orders",
        null=True,
        blank=True,
    )

    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE, default="cod")
    order_number = models.CharField(
        max_length=20, unique=True, default="", null=True, blank=True
    )
    customer_name = models.CharField(max_length=100)
    customer_email = models.EmailField(null=True, blank=True)
    customer_phone = models.CharField(max_length=15, null=True, blank=True)
    city = models.CharField(max_length=255, null=True, blank=True)
    customer_address = models.CharField(max_length=255, null=True, blank=True)
    shipping_address = models.CharField(max_length=255, null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    delivery_charge = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=ORDER_STATUS, default="pending")
    is_paid = models.BooleanField(default=False)
    transaction_id = models.CharField(max_length=255, null=True, blank=True)
    is_manual = models.BooleanField(default=False)
    dash_tracking_code = models.CharField(max_length=255, null=True, blank=True)
    promo_code = models.ForeignKey(
        PromoCode, on_delete=models.CASCADE, null=True, blank=True
    )
    note = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.customer_name} - {self.status}"

    def save(self, *args, **kwargs):
        if not self.id:  # first save (no ID yet)
            super().save(*args, **kwargs)
            self.order_number = self.generate_order_number()
            super().save(update_fields=["order_number"])
        else:
            super().save(*args, **kwargs)

    def generate_order_number(self):
        # Convert id to a hash and take first 8 hex digits
        hashed = hashlib.md5(str(self.id).encode()).hexdigest()[:8].upper()
        return f"ORD-{hashed}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, null=True, blank=True
    )
    variant = models.ForeignKey(
        "product.ProductVariant",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="order_items",
    )
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.variant:
            return f"{self.variant} - {self.quantity}"
        return f"{self.product.name} - {self.quantity}"
