from django.urls import path

from .views import (
    CollectionDataListCreateView,
    CollectionDataRetrieveUpdateDestroyView,
    CollectionListCreateView,
    CollectionRetrieveUpdateDestroyView,
)

urlpatterns = [
    # Collection endpoints
    path(
        "collections/",
        CollectionListCreateView.as_view(),
        name="collection-list-create",
    ),
    path(
        "collections/<slug:slug>/",
        CollectionRetrieveUpdateDestroyView.as_view(),
        name="collection-retrieve-update-destroy",
    ),
    # Collection Data endpoints (nested under collection slug)
    path(
        "collections/<slug:slug>/data/",
        CollectionDataListCreateView.as_view(),
        name="collection-data-list-create",
    ),
    path(
        "collections/<slug:slug>/data/<int:pk>/",
        CollectionDataRetrieveUpdateDestroyView.as_view(),
        name="collection-data-retrieve-update-destroy",
    ),
]
