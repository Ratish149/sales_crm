from django.urls import path

from .views import (
    NepdoraPaymentListCreateView,
    NepdoraPaymentRetrieveUpdateDestroyView,
    TenantCentralPaymentHistoryListCreateView,
    TenantCentralPaymentHistoryRetrieveUpdateDestroyView,
    TenantTransferHistoryListCreateView,
    TenantTransferHistoryRetrieveUpdateDestroyView,
    PaymentSummaryAPIView,
)

urlpatterns = [
    # NepdoraPayment gateway credentials
    path('nepdora-payments/', NepdoraPaymentListCreateView.as_view(), name='nepdora-payment-list-create'),
    path('nepdora-payments/<int:pk>/', NepdoraPaymentRetrieveUpdateDestroyView.as_view(), name='nepdora-payment-detail'),

    # Central payment history (all tenant transactions flowing through Nepdora)
    path('tenant-central-payments/', TenantCentralPaymentHistoryListCreateView.as_view(), name='tenant-central-payment-list-create'),
    path('tenant-central-payments/<int:pk>/', TenantCentralPaymentHistoryRetrieveUpdateDestroyView.as_view(), name='tenant-central-payment-detail'),

    # Manual transfer history (admin → tenant)
    path('tenant-transfers/', TenantTransferHistoryListCreateView.as_view(), name='tenant-transfer-list-create'),
    path('tenant-transfers/<int:pk>/', TenantTransferHistoryRetrieveUpdateDestroyView.as_view(), name='tenant-transfer-detail'),

    # Summary: totals of received vs paid
    path('payment-summary/', PaymentSummaryAPIView.as_view(), name='payment-summary'),
]
