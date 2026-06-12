from django.urls import path

from .views import FBPixelListCreateView, FBPixelRetrieveUpdateDestroyView

urlpatterns = [
    path(
        "fb-pixel/",
        FBPixelListCreateView.as_view(),
        name="fb-pixel-list-create",
    ),
    path(
        "fb-pixel/<int:pk>/",
        FBPixelRetrieveUpdateDestroyView.as_view(),
        name="fb-pixel-detail",
    ),
]
