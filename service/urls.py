from django.urls import path

from .views import (
    ServiceBulkCreateView,
    ServiceCategoryListCreateView,
    ServiceCategoryRetrieveUpdateDestroyView,
    ServiceListCreateView,
    ServiceRetrieveUpdateDestroyView,
)

urlpatterns = [
    path("service/", ServiceListCreateView.as_view(), name="service_list_create"),
    path(
        "service-bulk-create/",
        ServiceBulkCreateView.as_view(),
        name="service_bulk_create",
    ),
    path(
        "service/<slug:slug>/",
        ServiceRetrieveUpdateDestroyView.as_view(),
        name="service_retrieve_update_destroy",
    ),
    path(
        "service-category/",
        ServiceCategoryListCreateView.as_view(),
        name="service_category_list_create",
    ),
    path(
        "service-category/<slug:slug>/",
        ServiceCategoryRetrieveUpdateDestroyView.as_view(),
        name="service_category_retrieve_update_destroy",
    ),
]
