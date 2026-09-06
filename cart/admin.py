from django.contrib import admin

from cart.models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    fields = ["product", "variant", "quantity", "price", "created_at"]
    readonly_fields = ["created_at"]


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    inlines = [CartItemInline]
    list_display = [
        "id",
        "contact_name",
        "contact_phone",
        "contact_email",
        "status",
        "total_amount",
        "total_items",
        "last_activity_at",
        "abandoned_at",
        "recovered_at",
        "created_at",
    ]
    list_filter = ["status", "created_at", "last_activity_at"]
    search_fields = ["id", "contact_name", "contact_phone", "contact_email"]
    readonly_fields = [
        "id",
        "last_activity_at",
        "abandoned_at",
        "recovered_at",
        "created_at",
        "updated_at",
    ]


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ["id", "cart", "product", "variant", "quantity", "price", "created_at"]
    search_fields = ["cart__id", "product__name", "variant__name"]
