from django.urls import path

from .views import (
    DashboardStatsView,
    MyOrderListAPIView,
    MyOrderStatusView,
    OrderListCreateAPIView,
    OrderRetrieveUpdateDestroyAPIView,
)

urlpatterns = [
    path("order/", OrderListCreateAPIView.as_view(), name="order-list-create"),
    path(
        "order/<int:pk>/",
        OrderRetrieveUpdateDestroyAPIView.as_view(),
        name="order-retrieve-update-destroy",
    ),
    path("dashboard-stats/", DashboardStatsView.as_view(), name="dashboard-stats"),
    path("my-order-list/", MyOrderListAPIView.as_view(), name="customer-order"),
    path("my-order-status/", MyOrderStatusView.as_view(), name="customer-order-status"),
]
