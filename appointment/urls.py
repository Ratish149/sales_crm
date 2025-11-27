from django.urls import path

from .views import (
    AppointmentListCreateView,
    AppointmentReasonListCreateView,
    AppointmentReasonRetrieveUpdateDestroyView,
    AppointmentRetrieveUpdateDestroyView,
)

urlpatterns = [
    path("appointment-reasons/", AppointmentReasonListCreateView.as_view()),
    path(
        "appointment-reasons/<int:pk>/",
        AppointmentReasonRetrieveUpdateDestroyView.as_view(),
    ),
    path("appointments/", AppointmentListCreateView.as_view()),
    path("appointments/<int:pk>/", AppointmentRetrieveUpdateDestroyView.as_view()),
]
