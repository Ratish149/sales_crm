from django.urls import path

from .views import GalleryListCreateView, GalleryRetrieveUpdateDestroyView

urlpatterns = [
    path("gallery/", GalleryListCreateView.as_view(), name="gallery-list-create"),
    path(
        "gallery/<int:pk>/",
        GalleryRetrieveUpdateDestroyView.as_view(),
        name="gallery-detail",
    ),
]
