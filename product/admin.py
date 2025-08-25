from django.contrib import admin
from django.db import models
from .models import Product, ProductImage, Category, SubCategory
from tinymce.widgets import TinyMCE
# Register your models here.


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)
    list_per_page = 25


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)
    list_per_page = 25


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    list_display = ('product', 'image')
    search_fields = ('product',)
    list_per_page = 25
    extra = 0
    tab = True


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'price', 'stock')
    search_fields = ('name', 'description')
    list_per_page = 25
    inlines = [ProductImageInline]
    formfield_overrides = {
        models.TextField: {'widget': TinyMCE()}
    }
