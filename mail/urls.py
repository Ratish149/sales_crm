from django.urls import path

from .views import SendPaymentEmailAPIView

urlpatterns = [
    path(
        "send-payment-email/",
        SendPaymentEmailAPIView.as_view(),
        name="send-payment-email",
    ),
]
