from django.contrib import admin
from tinymce.widgets import TinyMCE

from .models import (
    Category,
    PricingMetric,
    Product,
    ProductComposition,
    ProductImage,
    ProductOption,
    ProductOptionValue,
    ProductReview,
    ProductVariant,
    SubCategory,
    Wishlist,
)

# Register your models here.


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "id")
    search_fields = ("name",)
    list_per_page = 25


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "id")
    search_fields = ("name",)
    list_per_page = 25


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    list_display = ("product", "image")
    search_fields = ("product",)
    list_per_page = 25
    extra = 0


class ProductCompositionInline(admin.TabularInline):
    model = ProductComposition
    extra = 1
    autocomplete_fields = ["metric"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "final_price", "stock", "use_dynamic_pricing")
    search_fields = ["name"]
    list_per_page = 25
    inlines = [ProductImageInline, ProductCompositionInline]

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == "content":
            return db_field.formfield(widget=TinyMCE())
        return super().formfield_for_dbfield(db_field, **kwargs)


@admin.register(ProductOption)
class ProductOptionAdmin(admin.ModelAdmin):
    list_display = ("product", "name")
    search_fields = ("product", "name")
    list_per_page = 25


@admin.register(ProductOptionValue)
class ProductOptionValueAdmin(admin.ModelAdmin):
    list_display = ("option", "value")
    search_fields = ("option", "value")
    list_per_page = 25


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("product", "price", "stock")
    search_fields = ("product", "price", "stock")
    list_per_page = 25


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "user", "review", "rating")
    search_fields = ("product", "user")
    list_per_page = 25


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ("product", "user")
    search_fields = ("product", "user")
    list_per_page = 25


@admin.register(PricingMetric)
class PricingMetricAdmin(admin.ModelAdmin):
    list_display = ("name", "price_per_unit", "unit", "last_updated")
    search_fields = ("name",)
    list_per_page = 25
