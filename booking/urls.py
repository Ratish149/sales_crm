# urls.py
from django.urls import path

from .views import (
    BookingListCreateView,
    BookingRetrieveUpdateDestroyView,
    MyBookingListView,
)

urlpatterns = [
    path("bookings/", BookingListCreateView.as_view(), name="booking-list-create"),
    path(
        "bookings/<int:pk>/",
        BookingRetrieveUpdateDestroyView.as_view(),
        name="booking-detail",
    ),
    path("bookings/my/", MyBookingListView.as_view(), name="my-bookings"),
]
