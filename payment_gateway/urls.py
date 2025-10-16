from django.urls import path

from .views import (
    PaymentListAPIView,
    PaymentListCreateAPIView,
    PaymentRetrieveUpdateDestroyAPIView,
)

urlpatterns = [
    path(
        "payment-gateway/list/",
        PaymentListCreateAPIView.as_view(),
        name="payment-list-create",
    ),
    path(
        "payment-gateway/<int:pk>/",
        PaymentRetrieveUpdateDestroyAPIView.as_view(),
        name="payment-retrieve-update-destroy",
    ),
    path(
        "payment-gateway/",
        PaymentListAPIView.as_view(),
        name="payment-list",
    ),
]
