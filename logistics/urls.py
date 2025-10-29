from django.urls import path

from .views import LogisticsListCreateView, LogisticsRetrieveUpdateDestroyView

urlpatterns = [
    path("logistics/", LogisticsListCreateView.as_view(), name="logistics-list-create"),
    path(
        "logistics/<int:pk>",
        LogisticsRetrieveUpdateDestroyView.as_view(),
        name="logistics-retrieve-update-destroy",
    ),
]
