from django.urls import path

from .views import ServiceListCreateView, ServiceRetrieveUpdateDestroyView

urlpatterns = [
    path("service/", ServiceListCreateView.as_view(), name="service_list_create"),
    path(
        "service/<slug:slug>/",
        ServiceRetrieveUpdateDestroyView.as_view(),
        name="service_retrieve_update_destroy",
    ),
]
