from django.urls import path

from .views import (
    DefaultDeliveryChargeListCreateView,
    DeliveryChargeListCreateView,
    DeliveryChargeRetrieveUpdateDestroyView,
    LoadDefaultLocationsAPIView,
)

urlpatterns = [
    path(
        "delivery-charges/",
        DeliveryChargeListCreateView.as_view(),
        name="delivery-charge-list-create",
    ),
    path(
        "default-delivery-charges/",
        DefaultDeliveryChargeListCreateView.as_view(),
        name="default-delivery-charge-list-create",
    ),
    path(
        "delivery-charges/<int:pk>/",
        DeliveryChargeRetrieveUpdateDestroyView.as_view(),
        name="delivery-charge-detail",
    ),
    path(
        "delivery-charges/load-default/",
        LoadDefaultLocationsAPIView.as_view(),
        name="load-default-locations",
    ),
]
