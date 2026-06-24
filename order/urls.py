from django.urls import path

from .views import (
    AdminOrderListAPIView,
    CustomerOrderListAPIView,
    DashboardStatsView,
    MyOrderListAPIView,
    MyOrderStatusView,
    OrderExcelExportView,
    OrderGetAPIView,
    OrderListCreateAPIView,
    OrderRetrieveUpdateDestroyAPIView,
    OrderStorageStatsView,
    SendOrderToLogisticsAPIView,
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
    path("get-order/<str:order_number>/", OrderGetAPIView.as_view(), name="order-get"),
    path("dashboard-stats/", DashboardStatsView.as_view(), name="dashboard-stats"),
    path("my-order/", MyOrderListAPIView.as_view(), name="customer-order"),
    path("my-order-status/", MyOrderStatusView.as_view(), name="customer-order-status"),
    path("admin-order/", AdminOrderListAPIView.as_view(), name="admin-order"),
    path(
        "customer-orders/", CustomerOrderListAPIView.as_view(), name="customer-orders"
    ),
]
