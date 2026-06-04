from django.urls import path

from .views import InvoiceListCreateAPIView, InvoiceRetrieveUpdateDestroyAPIView

urlpatterns = [
    path("invoice/", InvoiceListCreateAPIView.as_view(), name="invoice-list-create"),
    path(
        "invoice/<int:pk>/",
        InvoiceRetrieveUpdateDestroyAPIView.as_view(),
        name="invoice-retrieve-update-destroy",
    ),
]
