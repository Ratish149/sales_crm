from django_filters import rest_framework as drf_filters
from rest_framework import filters, generics
from rest_framework.permissions import IsAuthenticated

from sales_crm.authentication import TenantJWTAuthentication
from sales_crm.pagination import CustomPagination

from .models import Event
from .serializers import EventListSerializer, EventSerializer


class EventFilterSet(drf_filters.FilterSet):
    # Boolean flag
    is_featured = drf_filters.BooleanFilter(field_name="is_featured")

    # Date range filters on start_date
    start_date_from = drf_filters.DateFilter(field_name="start_date", lookup_expr="gte")
    start_date_to = drf_filters.DateFilter(field_name="start_date", lookup_expr="lte")

    # Location filters
    city = drf_filters.CharFilter(field_name="city", lookup_expr="icontains")
    country = drf_filters.CharFilter(field_name="country", lookup_expr="icontains")

    # Tag partial match
    tags = drf_filters.CharFilter(field_name="tags", lookup_expr="icontains")

    class Meta:
        model = Event
        fields = [
            "is_featured",
            "start_date_from",
            "start_date_to",
            "city",
            "country",
            "tags",
        ]


class EventListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/events/   → list all events (public, filterable, searchable)
    POST /api/events/   → create an event (JWT auth required)
    """

    pagination_class = CustomPagination
    filter_backends = [
        drf_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = EventFilterSet
    search_fields = ["title", "tags"]
    ordering_fields = ["start_date", "created_at", "title"]
    ordering = ["-start_date"]

    def get_queryset(self):
        return Event.objects.only(
            "id",
            "title",
            "slug",
            "start_date",
            "end_date",
            "start_time",
            "city",
            "country",
            "venue_name",
            "thumbnail",
            "is_featured",
            "tags",
            "created_at",
        )

    def get_serializer_class(self):
        if self.request.method == "GET":
            return EventListSerializer
        return EventSerializer

    def get_authenticators(self):
        if self.request.method == "POST":
            return [TenantJWTAuthentication()]
        return []

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return []


class EventRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/events/<slug>/   → full event detail (public)
    PUT    /api/events/<slug>/   → full update (JWT auth required)
    PATCH  /api/events/<slug>/   → partial update (JWT auth required)
    DELETE /api/events/<slug>/   → delete (JWT auth required)
    """

    lookup_field = "slug"
    serializer_class = EventSerializer

    def get_queryset(self):
        return Event.objects.only(
            "id",
            "title",
            "slug",
            "start_date",
            "end_date",
            "start_time",
            "city",
            "country",
            "venue_name",
            "thumbnail",
            "is_featured",
            "tags",
            "created_at",
        )

    def get_authenticators(self):
        if self.request.method == "GET":
            return []
        return [TenantJWTAuthentication()]

    def get_permissions(self):
        if self.request.method == "GET":
            return []
        return [IsAuthenticated()]
