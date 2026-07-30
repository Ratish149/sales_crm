from django.urls import path

from .views import (
    GoogleAdSenseListCreateView,
    GoogleAdSenseRetrieveUpdateDestroyView,
)

urlpatterns = [
    path(
        "google-adsense/",
        GoogleAdSenseListCreateView.as_view(),
        name="google-adsense-list-create",
    ),
    path(
        "google-adsense/<int:pk>/",
        GoogleAdSenseRetrieveUpdateDestroyView.as_view(),
        name="google-adsense-detail",
    ),
]
