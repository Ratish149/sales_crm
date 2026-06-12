from django.urls import path

from .views import TawkToListCreateView, TawkToRetrieveUpdateDestroyView

urlpatterns = [
    path(
        "tawkto/",
        TawkToListCreateView.as_view(),
        name="tawkto-list-create",
    ),
    path(
        "tawkto/<int:pk>/",
        TawkToRetrieveUpdateDestroyView.as_view(),
        name="tawkto-detail",
    ),
]
