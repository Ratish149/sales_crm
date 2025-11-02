from django.urls import path

from .views import GoogleAnalyticListCreateView, GoogleAnalyticRetrieveUpdateDestroyView

urlpatterns = [
    path(
        "google-analytic/",
        GoogleAnalyticListCreateView.as_view(),
        name="google-analytic-list-create",
    ),
    path(
        "google-analytic/<int:pk>/",
        GoogleAnalyticRetrieveUpdateDestroyView.as_view(),
        name="google-analytic-detail",
    ),
]
