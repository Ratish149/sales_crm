from django.urls import path

from .views import FacebookListCreateView, FacebookRetrieveUpdateDestroyView

urlpatterns = [
    path("facebook/", FacebookListCreateView.as_view(), name="facebook-list-create"),
    path(
        "facebook/<int:pk>",
        FacebookRetrieveUpdateDestroyView.as_view(),
        name="facebook-retrieve-update-destroy",
    ),
]
