from django.contrib import admin
from .models import Product
from unfold.admin import ModelAdmin

# Register your models here.


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    list_display = ('name', 'description', 'price', 'stock')
    search_fields = ('name', 'description')
    list_filter = ('stock',)
    list_per_page = 25
