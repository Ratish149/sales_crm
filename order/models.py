from django.db import models
from product.models import Product
# Create your models here.


class Order(models.Model):
    ORDER_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    customer = models.ForeignKey(
        'customer.Customer', on_delete=models.CASCADE, related_name='orders', null=True, blank=True)
    order_number = models.CharField(
        max_length=20, unique=True, default="", null=True, blank=True)
    customer_name = models.CharField(max_length=100)
    customer_email = models.EmailField(null=True, blank=True)
    customer_phone = models.CharField(max_length=15, null=True, blank=True)
    customer_address = models.CharField(max_length=255)
    shipping_address = models.CharField(max_length=255)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20, choices=ORDER_STATUS, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
        return f"ORD-{self.id:06d}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product.name} - {self.quantity}"
