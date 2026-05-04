from django.db import transaction
from django_filters import rest_framework as django_filters
from rest_framework import filters, generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from sales_crm.authentication import TenantJWTAuthentication

from .models import Service, ServiceCategory
from .serializers import (
    BulkCreateServiceSerializer,
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
    queryset = Service.objects.all().order_by("-created_at")
    serializer_class = ServiceSerializer
    pagination_class = CustomPagination
    filter_backends = [django_filters.DjangoFilterBackend, filters.SearchFilter]
    filterset_class = ServiceFilterSet
    search_fields = ["title"]

    def get_authenticators(self):
        if self.request.method == "POST":
            return [TenantJWTAuthentication()]
        return []

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.request.method == "GET":
            return ServiceListSerializer
        return ServiceSerializer


class ServiceRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    lookup_field = "slug"

    def get_authenticators(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [TenantJWTAuthentication()]
        return []

    def get_permissions(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [IsAuthenticated()]
        return super().get_permissions()


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


class ServiceBulkCreateView(APIView):
    """
    POST /api/services/bulk-create/

    Accepts a JSON body with a `services` list and creates all of them
    inside a single database transaction.

    Request body example:
    {
      "services": [
        {
          "title": "Service One",
          "description": "<p>...</p>",
          "meta_title": "...",
          "meta_description": "...",
          "service_category_name": "Consulting"
        },
        { ... }
      ]
    }

    Response on success (201):
    {
      "created": 3,
      "services": [ <ServiceSerializer data for each created service> ]
    }
    """

    authentication_classes = [TenantJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = BulkCreateServiceSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        services_data = serializer.validated_data["services"]
        created_services = []

        for item in services_data:
            category_name = item.pop("service_category_name", None)
            # Resolve category
            category = None
            if category_name:
                category = ServiceCategory.objects.filter(
                    name__icontains=category_name
                ).first()
                if not category:
                    category = ServiceCategory.objects.create(name=category_name)

            if category:
                item["service_category"] = category

            # Deduplicate titles
            title = item["title"]
            if Service.objects.filter(title=title).exists():
                suffix = 1
                while Service.objects.filter(title=f"{title} ({suffix})").exists():
                    suffix += 1
                item["title"] = f"{title} ({suffix})"

            service = Service.objects.create(**item)
            created_services.append(service)

        response_data = ServiceSerializer(created_services, many=True).data
        return Response(
            {"created": len(created_services), "services": response_data},
            status=status.HTTP_201_CREATED,
        )
