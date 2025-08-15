from django.contrib import admin
from .models import Order, OrderItem
# Register your models here.


class OrderItem(admin.TabularInline):
    model = OrderItem
    tab = True


class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderItem]
    list_display = ['customer_name', 'customer_email', 'customer_address',
                    'shipping_address', 'total_amount', 'created_at', 'updated_at']
    search_fields = ['customer_name']


admin.site.register(Order, OrderAdmin)
