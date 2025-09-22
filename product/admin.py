from django.contrib import admin
from django.db import models
from tinymce.widgets import TinyMCE

from .models import (
    Category,
    Product,
    ProductImage,
    ProductReview,
    SubCategory,
    Wishlist,
)

# Register your models here.


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)
    list_per_page = 25


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)
    list_per_page = 25


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    list_display = ("product", "image")
    search_fields = ("product",)
    list_per_page = 25
    extra = 0
    tab = True


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "price", "stock")
    search_fields = ("name", "description")
    list_per_page = 25
    inlines = [ProductImageInline]
    formfield_overrides = {models.TextField: {"widget": TinyMCE()}}


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
