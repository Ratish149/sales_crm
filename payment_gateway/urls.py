from django.urls import path

from .views import (
    PaymentHistoryListCreateAPIView,
    PaymentHistoryRetrieveUpdateDestroyAPIView,
    PaymentListAPIView,
    PaymentListCreateAPIView,
    PaymentQRListCreateAPIView,
    PaymentQRRetrieveUpdateDestroyAPIView,
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
    path(
        "payment-gateway/history/",
        PaymentHistoryListCreateAPIView.as_view(),
        name="payment-history-list-create",
    ),
    path(
        "payment-gateway/history/<int:pk>/",
        PaymentHistoryRetrieveUpdateDestroyAPIView.as_view(),
        name="payment-history-retrieve-update-destroy",
    ),
    path(
        "payment-gateway-qr/",
        PaymentQRListCreateAPIView.as_view(),
        name="payment-qr-list-create",
    ),
    path(
        "payment-gateway-qr/<int:pk>/",
        PaymentQRRetrieveUpdateDestroyAPIView.as_view(),
        name="payment-qr-retrieve-update-destroy",
    ),
]
