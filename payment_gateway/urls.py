from django.urls import path

from .views import PaymentListCreateAPIView, PaymentRetrieveUpdateDestroyAPIView

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
]
