# filters.py
import django_filters

from .models import Booking


class BookingFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=Booking.STATUS_CHOICES)
    payment_status = django_filters.ChoiceFilter(choices=Booking.PAYMENT_STATUS_CHOICES)

    booking_type = django_filters.CharFilter(lookup_expr="icontains")
    booking_name = django_filters.CharFilter(lookup_expr="icontains")
    customer_name = django_filters.CharFilter(lookup_expr="icontains")
    customer_email = django_filters.CharFilter(lookup_expr="icontains")

    # Date range:  ?start_date_after=2025-01-01&start_date_before=2025-06-01
    start_date = django_filters.DateTimeFromToRangeFilter()
    end_date = django_filters.DateTimeFromToRangeFilter()

    # Amount range: ?total_amount_min=100&total_amount_max=5000
    total_amount = django_filters.RangeFilter()

    class Meta:
        model = Booking
        fields = [
            "status",
            "payment_status",
            "booking_type",
            "booking_name",
            "customer_name",
            "customer_email",
            "start_date",
            "end_date",
            "total_amount",
            "user",
        ]
