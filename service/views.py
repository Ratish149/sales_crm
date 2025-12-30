from django_filters import rest_framework as django_filters
from rest_framework import filters, generics

# Create your views here.
from rest_framework.pagination import PageNumberPagination

from .models import Service, ServiceCategory
from .serializers import (
    ServiceCategorySerializer,
    ServiceListSerializer,
    ServiceSerializer,
)


class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class ServiceFilterSet(django_filters.FilterSet):
    service_category = django_filters.CharFilter(
        field_name="service_category__slug", lookup_expr="iexact"
    )

    class Meta:
        model = Service
        fields = ["service_category"]


class ServiceListCreateView(generics.ListCreateAPIView):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    pagination_class = CustomPagination
    filter_backends = [django_filters.DjangoFilterBackend, filters.SearchFilter]
    filterset_class = ServiceFilterSet
    search_fields = ["title"]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return ServiceListSerializer
        return ServiceSerializer


class ServiceRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    lookup_field = "slug"


class ServiceCategoryListCreateView(generics.ListCreateAPIView):
    queryset = ServiceCategory.objects.all()
    serializer_class = ServiceCategorySerializer
    pagination_class = CustomPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ["name"]


class ServiceCategoryRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ServiceCategory.objects.all()
    serializer_class = ServiceCategorySerializer
    lookup_field = "slug"
