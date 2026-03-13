from django.urls import path

from .views import (
    PaymentHistoryListCreateAPIView,
    PaymentHistoryRetrieveUpdateDestroyAPIView,
    PaymentListAPIView,
    PaymentListCreateAPIView,
    PaymentRetrieveUpdateDestroyAPIView,
)

urlpatterns = [
    path(
        "payment-gateway/",
        PaymentListCreateAPIView.as_view(),
        name="payment-list-create",
    ),
    path(
        "payment-gateway/<int:pk>/",
        PaymentRetrieveUpdateDestroyAPIView.as_view(),
        name="payment-retrieve-update-destroy",
    ),
    path(
        "payment-gateway/list/",
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
]
