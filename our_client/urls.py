from django.urls import path

from .views import OurClientListCreateView, OurClientRetrieveUpdateDestroyView

urlpatterns = [
    path(
        "our-client/", OurClientListCreateView.as_view(), name="our-client-list-create"
    ),
    path(
        "our-client/<int:pk>/",
        OurClientRetrieveUpdateDestroyView.as_view(),
        name="our-client-retrieve-update-destroy",
    ),
]
