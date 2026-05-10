# views.py
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics
from rest_framework.permissions import IsAuthenticated

from .filters import BookingFilter
from .models import Booking
from .serializers import BookingListSerializer, BookingSerializer


class BookingListCreateView(generics.ListCreateAPIView):
    """
    GET  /bookings/  → all bookings (no user filter)
    POST /bookings/  → create booking
                       - with token: user auto-attached
                       - without token: guest booking (user=null)
    """

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = BookingFilter
    search_fields = [
        "customer_name",
        "customer_email",
        "booking_name",
        "booking_type",
        "transaction_id",
    ]
    ordering_fields = [
        "created_at",
        "updated_at",
        "start_date",
        "end_date",
        "total_amount",
    ]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return BookingListSerializer
        return BookingSerializer

    def get_queryset(self):
        return Booking.objects.select_related("user").only(
            "id",
            "status",
            "payment_status",
            "booking_type",
            "booking_name",
            "customer_name",
            "customer_email",
            "customer_phone",
            "start_date",
            "end_date",
            "guests",
            "total_amount",
            "amount_paid",
            "transaction_id",
            "notes",
            "extras",
            "created_at",
            "updated_at",
            "user_id",
        )

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(user=user)


class BookingRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PUT/PATCH/DELETE  /bookings/<pk>/
    """

    serializer_class = BookingSerializer

    def get_queryset(self):
        return Booking.objects.select_related("user")


class MyBookingListView(generics.ListAPIView):
    """
    GET /bookings/my/  → logged-in user's bookings only
    """

    serializer_class = BookingListSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = BookingFilter
    search_fields = ["booking_name", "booking_type", "transaction_id"]
    ordering_fields = ["created_at", "start_date", "total_amount"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return (
            Booking.objects
            .select_related("user")
            .filter(user=self.request.user)
            .only(
                "id",
                "status",
                "payment_status",
                "booking_type",
                "booking_name",
                "customer_name",
                "customer_email",
                "customer_phone",
                "start_date",
                "end_date",
                "guests",
                "total_amount",
                "amount_paid",
                "transaction_id",
                "notes",
                "extras",
                "created_at",
                "updated_at",
                "user_id",
            )
        )
