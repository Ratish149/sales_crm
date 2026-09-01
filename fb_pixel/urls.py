from django.urls import path

from .views import (
    FBPixelListCreateView,
    FBPixelRetrieveUpdateDestroyView,
    MetaCommerceListCreateView,
    MetaCommerceRetrieveUpdateDestroyView,
)

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
    path(
        "meta-commerce/",
        MetaCommerceListCreateView.as_view(),
        name="meta-commerce-list-create",
    ),
    path(
        "meta-commerce/<int:pk>/",
        MetaCommerceRetrieveUpdateDestroyView.as_view(),
        name="meta-commerce-detail",
    ),
]
