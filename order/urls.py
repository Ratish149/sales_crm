from django.urls import path

from .views import (
    AdminOrderListAPIView,
    CustomerOrderListAPIView,
    DashboardStatsView,
    MyOrderListAPIView,
    MyOrderStatusView,
    NCMCreateOrderAPIView,
    NCMWebhookAPIView,
    OrderExcelExportView,
    OrderGetAPIView,
    OrderListCreateAPIView,
    OrderRetrieveUpdateDestroyAPIView,
    OrderStorageStatsView,
    SendOrderToLogisticsAPIView,
    SendOrderToNCMAPIView,
)

urlpatterns = [
    path("order/", OrderListCreateAPIView.as_view(), name="order-list-create"),
    path(
        "order-storage-stats/",
        OrderStorageStatsView.as_view(),
        name="order-storage-stats",
    ),
    path(
        "order-export/",
        OrderExcelExportView.as_view(),
        name="order-export",
    ),
    path(
        "order/<int:pk>/",
        OrderRetrieveUpdateDestroyAPIView.as_view(),
        name="order-retrieve-update-destroy",
    ),
    path(
        "order/<int:pk>/send-order/",
        SendOrderToLogisticsAPIView.as_view(),
        name="order-send-to-logistics",
    ),
    path(
        "order/<int:pk>/send-ncm/",
        SendOrderToNCMAPIView.as_view(),
        name="order-send-to-ncm",
    ),
    path(
        "order/ncm/create/",
        NCMCreateOrderAPIView.as_view(),
        name="ncm-order-create",
    ),
    path(
        "order/ncm/webhook/<str:schema_name>/",
        NCMWebhookAPIView.as_view(),
        name="ncm-webhook-schema",
    ),
    path("get-order/<str:order_number>/", OrderGetAPIView.as_view(), name="order-get"),
    path("dashboard-stats/", DashboardStatsView.as_view(), name="dashboard-stats"),
    path("my-order/", MyOrderListAPIView.as_view(), name="customer-order"),
    path("my-order-status/", MyOrderStatusView.as_view(), name="customer-order-status"),
    path("admin-order/", AdminOrderListAPIView.as_view(), name="admin-order"),
    path(
        "customer-orders/", CustomerOrderListAPIView.as_view(), name="customer-orders"
    ),
]
