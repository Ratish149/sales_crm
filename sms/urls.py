from django.urls import path

from .views import (
    AdminSMSListCreateView,
    SendCustomSMSView,
    SMSBalanceView,
    SMSPurchaseDetailView,
    SMSPurchaseListCreateView,
    SMSSendHistoryDetailView,
    SMSSendHistoryListCreateView,
)

urlpatterns = [
    path(
        "sms/purchases/", SMSPurchaseListCreateView.as_view(), name="sms-purchase-list"
    ),
    path(
        "sms/purchases/<int:pk>/",
        SMSPurchaseDetailView.as_view(),
        name="sms-purchase-detail",
    ),
    path(
        "sms/history/", SMSSendHistoryListCreateView.as_view(), name="sms-history-list"
    ),
    path(
        "sms/history/<int:pk>/",
        SMSSendHistoryDetailView.as_view(),
        name="sms-history-detail",
    ),
    path("sms/balance/", SMSBalanceView.as_view(), name="sms-balance"),
    path(
        "sms/admin/purchases/",
        AdminSMSListCreateView.as_view(),
        name="admin-sms-purchase-list",
    ),
    path("sms/send-sms/", SendCustomSMSView.as_view(), name="sms-send-sms"),
]
