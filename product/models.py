from django.db import models
from django.utils.text import slugify

from customer.models import Customer
from sales_crm.utils.file_size_validator import file_size


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    image = models.FileField(
        upload_to="category_images", null=True, blank=True, validators=[file_size]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        unique_together = ("name", "slug")


class SubCategory(models.Model):
    category = models.ForeignKey(
        "Category", on_delete=models.CASCADE, null=True, blank=True
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    image = models.FileField(
        upload_to="sub_category_images", null=True, blank=True, validators=[file_size]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        unique_together = ("name", "slug")


class ProductImage(models.Model):
    product = models.ForeignKey(
        "Product",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="images",
    )
    image = models.FileField(
        upload_to="product_images",
        validators=[file_size],
        null=True,
        blank=True,
        max_length=255,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Product(models.Model):
    STATUS_CHOICES = (
        ("active", "Active"),
        ("draft", "Draft"),
        ("archived", "Archived"),
    )
    name = models.TextField(null=True, blank=True)
    slug = models.SlugField(null=True, blank=True, max_length=255)
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=100, decimal_places=2)
    market_price = models.DecimalField(
        max_digits=100, decimal_places=2, null=True, blank=True
    )
    track_stock = models.BooleanField(default=True)
    stock = models.IntegerField(null=True, blank=True)
    weight = models.CharField(max_length=100, null=True, blank=True)
    thumbnail_image = models.FileField(
        upload_to="product_images",
        validators=[file_size],
        null=True,
        blank=True,
        max_length=255,
    )
    thumbnail_alt_description = models.CharField(max_length=100, null=True, blank=True)
    category = models.ForeignKey(
        "Category", on_delete=models.CASCADE, null=True, blank=True
    )
    sub_category = models.ForeignKey(
        "SubCategory", on_delete=models.CASCADE, null=True, blank=True
    )
    is_popular = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="active")

    meta_title = models.CharField(max_length=255, null=True, blank=True)
    meta_description = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        unique_together = ("name", "slug")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["category"]),
            models.Index(fields=["sub_category"]),
            models.Index(fields=["is_popular"]),
            models.Index(fields=["is_featured"]),
        ]


class ProductOption(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.name


class ProductOptionValue(models.Model):
    option = models.ForeignKey(ProductOption, on_delete=models.CASCADE)
    value = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.value


class ProductVariant(models.Model):
    """Represents a combination like Size=S, Color=Black"""

    product = models.ForeignKey(
        Product, related_name="variants", on_delete=models.CASCADE
    )
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock = models.IntegerField(default=0, null=True, blank=True)
    image = models.FileField(upload_to="variant_images", null=True, blank=True)
    option_values = models.ManyToManyField(
        ProductOptionValue, related_name="variants", blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        values = ", ".join(v.value for v in self.option_values.all())
        return f"{self.product.name} ({values})"


class ProductReview(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey(Customer, on_delete=models.CASCADE)
    review = models.TextField(null=True, blank=True)
    rating = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.product.name}"


class Wishlist(models.Model):
    user = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} - {self.product.name}"
