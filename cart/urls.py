from django.urls import path

from cart.views import (
    AdminCartListAPIView,
    CartContactUpdateAPIView,
    CartCreateAPIView,
    CartDetailAPIView,
    CartItemAddAPIView,
    CartItemDeleteAPIView,
    CartSweepAbandonedAPIView,
    MyActiveCartAPIView,
)

urlpatterns = [
    path("cart/", CartCreateAPIView.as_view(), name="cart-create"),
    path("cart/active/", MyActiveCartAPIView.as_view(), name="my-active-cart"),
    path("cart/<uuid:pk>/", CartDetailAPIView.as_view(), name="cart-detail"),
    path("cart/<uuid:pk>/items/", CartItemAddAPIView.as_view(), name="cart-item-add"),
    path(
        "cart/<uuid:pk>/items/<int:item_id>/",
        CartItemDeleteAPIView.as_view(),
        name="cart-item-delete",
    ),
    path(
        "cart/<uuid:pk>/contact/",
        CartContactUpdateAPIView.as_view(),
        name="cart-contact-update",
    ),
    path("carts/", AdminCartListAPIView.as_view(), name="admin-cart-list"),
    path(
        "carts/sweep-abandoned/",
        CartSweepAbandonedAPIView.as_view(),
        name="cart-sweep-abandoned",
    ),
]
