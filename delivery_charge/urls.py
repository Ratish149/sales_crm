from django.urls import path

from .views import (
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
