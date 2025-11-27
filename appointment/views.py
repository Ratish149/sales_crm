from django_filters import rest_framework as django_filters
from rest_framework import filters, generics
from rest_framework.pagination import PageNumberPagination

from .models import Appointment, AppointmentReason
from .serializers import AppointmentReasonSerializer, AppointmentSerializer


# Create your views here.
class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class AppointmentReasonListCreateView(generics.ListCreateAPIView):
    queryset = AppointmentReason.objects.all()
    serializer_class = AppointmentReasonSerializer


class AppointmentReasonRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = AppointmentReason.objects.all()
    serializer_class = AppointmentReasonSerializer


class AppointmentFilterSet(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name="status", lookup_expr="icontains")
    time = django_filters.TimeFilter(field_name="time", lookup_expr="icontains")
    date_from = django_filters.DateFilter(field_name="created_at", lookup_expr="gte")
    date_to = django_filters.DateFilter(field_name="created_at", lookup_expr="lte")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        date_from = self.data.get("date_from")
        date_to = self.data.get("date_to")

        # If only date_from is provided, override the filter to get that exact date
        if date_from and not date_to:
            self.filters["date_from"].lookup_expr = "date"  # exact date
            # Optional: remove date_to filter if you want
            if "date_to" in self.filters:
                del self.filters["date_to"]

    class Meta:
        model = Appointment
        fields = ["status", "time", "date_from", "date_to"]


class AppointmentListCreateView(generics.ListCreateAPIView):
    queryset = Appointment.objects.all()
    pagination_class = CustomPagination
    serializer_class = AppointmentSerializer
    filter_backends = [django_filters.DjangoFilterBackend, filters.SearchFilter]
    filterset_class = AppointmentFilterSet
    search_fields = ["full_name", "phone_number"]


class AppointmentRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
