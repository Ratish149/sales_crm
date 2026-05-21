from django.db import models
from django.db.models import Q
from django.utils.text import slugify

from customer.models import Customer
from sales_crm.utils.file_size_validator import file_size
from sales_crm.utils.s3bucket import PublicMediaStorage


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    image = models.FileField(
        upload_to="category_images",
        storage=PublicMediaStorage(),
        null=True,
        blank=True,
        validators=[file_size],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("name", "slug")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class SubCategory(models.Model):
    category = models.ForeignKey(
        "Category", on_delete=models.CASCADE, null=True, blank=True
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    image = models.FileField(
        upload_to="sub_category_images",
        storage=PublicMediaStorage(),
        null=True,
        blank=True,
        validators=[file_size],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("name", "slug")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class PricingMetric(models.Model):
    name = models.CharField(max_length=100)
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=50)  # e.g., "gram", "carat"
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.price_per_unit}/{self.unit}"


class ProductComposition(models.Model):
    product = models.ForeignKey(
        "Product", related_name="compositions", on_delete=models.CASCADE
    )
    metric = models.ForeignKey(PricingMetric, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=3)

    def __str__(self):
        return f"{self.product.name} - {self.metric.name} ({self.quantity} {self.metric.unit})"


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
        storage=PublicMediaStorage(),
        null=True,
        blank=True,
        max_length=255,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return (
            f"Image for {self.product.name}"
            if self.product
            else "Unassigned Product Image"
        )


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
    fast_shipping = models.BooleanField(default=False)
    warranty = models.CharField(max_length=250, null=True, blank=True)
    track_stock = models.BooleanField(default=True, null=True, blank=True)
    stock = models.IntegerField(null=True, blank=True)
    weight = models.CharField(max_length=100, null=True, blank=True)
    thumbnail_image = models.FileField(
        upload_to="product_images",
        validators=[file_size],
        storage=PublicMediaStorage(),
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

    use_dynamic_pricing = models.BooleanField(default=False)
    base_making_charge = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00
    )

    meta_title = models.CharField(max_length=255, null=True, blank=True)
    meta_description = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
            models.Index(fields=["status"]),
            models.Index(fields=["-created_at"]),
            models.Index(fields=["price"]),
            models.Index(fields=["category", "status", "-created_at"]),
            models.Index(fields=["sub_category", "status", "-created_at"]),
            models.Index(fields=["is_popular", "-created_at"]),
            models.Index(fields=["is_featured", "-created_at"]),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def final_price(self):
        if not self.use_dynamic_pricing:
            return self.price

        composition_price = sum(
            c.metric.price_per_unit * c.quantity for c in self.compositions.all()
        )
        return composition_price + self.base_making_charge

    @property
    def active_offer(self):
        from django.utils import timezone

        now = timezone.now()
        offers = (
            Offer.objects
            .filter(is_active=True, start_date__lte=now, end_date__gte=now)
            .filter(
                Q(products=self)
                | Q(categories=self.category)
                | Q(sub_categories=self.sub_category)
            )
            .distinct()
        )

        # Pick the best offer (highest discount value)
        return offers.order_by("-discount_value").first()

    @property
    def discounted_price(self):
        offer = self.active_offer
        base_price = self.final_price
        if not offer:
            return base_price

        if offer.offer_type == "percentage":
            from decimal import Decimal

            return base_price * (Decimal("1") - offer.discount_value / Decimal("100"))
        elif offer.offer_type == "fixed":
            from decimal import Decimal

            return max(Decimal("0.00"), base_price - offer.discount_value)
        return base_price


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
    image = models.FileField(
        upload_to="variant_images", storage=PublicMediaStorage(), null=True, blank=True
    )
    option_values = models.ManyToManyField(
        ProductOptionValue, related_name="variants", blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["price"]),
            models.Index(fields=["-created_at"]),
            models.Index(fields=["product", "price"]),
        ]

    def __str__(self):
        values = ", ".join(v.value for v in self.option_values.all())
        return f"{self.product.name} ({values})"

    @property
    def active_offer(self):
        return self.product.active_offer

    @property
    def discounted_price(self):
        offer = self.active_offer
        # Use variant price if set, otherwise use product's base price
        base_price = self.price if self.price is not None else self.product.final_price

        if not offer:
            return base_price

        if offer.offer_type == "percentage":
            from decimal import Decimal

            return base_price * (Decimal("1") - offer.discount_value / Decimal("100"))
        elif offer.offer_type == "fixed":
            from decimal import Decimal

            return max(Decimal("0.00"), base_price - offer.discount_value)
        return base_price


class ProductReview(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey(Customer, on_delete=models.CASCADE)
    review = models.TextField(null=True, blank=True)
    rating = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["rating"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.product.name}"


class Wishlist(models.Model):
    user = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "product"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.product.name}"


class Offer(models.Model):
    OFFER_TYPE_CHOICES = (
        ("percentage", "Percentage Discount"),
        ("fixed", "Fixed Amount Discount"),
    )
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    offer_type = models.CharField(
        max_length=20, choices=OFFER_TYPE_CHOICES, default="percentage"
    )
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    thumbnail = models.FileField(
        upload_to="offer_images",
        storage=PublicMediaStorage(),
        null=True,
        blank=True,
        validators=[file_size],
    )

    # Applicability/Rules
    products = models.ManyToManyField(
        "Product",
        related_name="offers",
        blank=True,
        help_text="The specific products required or applicable for this offer.",
    )
    categories = models.ManyToManyField(
        "Category",
        related_name="offers",
        blank=True,
        help_text="Applicable categories for the offer.",
    )
    sub_categories = models.ManyToManyField(
        "SubCategory",
        related_name="offers",
        blank=True,
        help_text="Applicable sub-categories for the offer.",
    )

    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @property
    def is_valid(self):
        from django.utils import timezone

        now = timezone.now()
        return self.is_active and self.start_date <= now <= self.end_date
