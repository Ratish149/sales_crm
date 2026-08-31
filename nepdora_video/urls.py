from django.urls import path

from .views import (
    NepdoraVideoListCreateView,
    NepdoraVideoRetrieveUpdateDestroyView,
)

urlpatterns = [
    path(
        "nepdora-videos/",
        NepdoraVideoListCreateView.as_view(),
        name="nepdora-video-list-create",
    ),
    path(
        "nepdora-videos/<int:pk>/",
        NepdoraVideoRetrieveUpdateDestroyView.as_view(),
        name="nepdora-video-detail",
    ),
]
