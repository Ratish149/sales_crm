from django.urls import path

from .views import EventListCreateView, EventRetrieveUpdateDestroyView

urlpatterns = [
    path("events/", EventListCreateView.as_view(), name="event-list-create"),
    path("events/<str:slug>/", EventRetrieveUpdateDestroyView.as_view(), name="event-detail"),
]
