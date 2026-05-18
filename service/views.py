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


# ─── Shared querysets ─────────────────────────────────────────────────────────

SERVICE_CATEGORY_QS = ServiceCategory.objects.only(
    "id",
    "name",
    "slug",
    "description",
    "thumbnail_image",
    "thumbnail_image_alt_description",
    "created_at",
    "updated_at",
)

# used for list (GET) — joins category so no N+1 per row
SERVICE_LIST_QS = (
    Service.objects
    .select_related("service_category")
    .only(
        "id",
        "title",
        "slug",
        "description",
        "thumbnail_image",
        "thumbnail_image_alt_description",
        "meta_title",
        "meta_description",
        "service_category_id",
        "service_category__name",
        "service_category__slug",
        "service_category__thumbnail_image",
        "service_category__thumbnail_image_alt_description",
        "service_category__created_at",
        "service_category__updated_at",
        "created_at",
        "updated_at",
    )
    .order_by("-created_at")
)

# used for detail / write views — no only() so updates aren't blocked
SERVICE_QS = Service.objects.select_related("service_category")


# ─── Filters ──────────────────────────────────────────────────────────────────


class ServiceFilterSet(django_filters.FilterSet):
    service_category = django_filters.CharFilter(
        field_name="service_category__slug", lookup_expr="iexact"
    )

    class Meta:
        model = Service
        fields = ["service_category"]


# ─── Service ──────────────────────────────────────────────────────────────────


class ServiceListCreateView(generics.ListCreateAPIView):
    serializer_class = ServiceSerializer
    pagination_class = CustomPagination
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = ServiceFilterSet
    search_fields = ["title"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        if self.request.method == "GET":
            return SERVICE_LIST_QS
        return Service.objects.all()

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
    queryset = SERVICE_QS
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


# ─── Service Category ─────────────────────────────────────────────────────────


class ServiceCategoryListCreateView(generics.ListCreateAPIView):
    queryset = SERVICE_CATEGORY_QS
    serializer_class = ServiceCategorySerializer
    pagination_class = CustomPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ["name"]


class ServiceCategoryRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = SERVICE_CATEGORY_QS
    serializer_class = ServiceCategorySerializer
    lookup_field = "slug"


# ─── Bulk Create ──────────────────────────────────────────────────────────────


class ServiceBulkCreateView(APIView):
    authentication_classes = [TenantJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = BulkCreateServiceSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        services_data = serializer.validated_data["services"]
        created_services = []

        # batch-fetch all matching categories in one query
        category_names = [
            item["service_category_name"]
            for item in services_data
            if item.get("service_category_name")
        ]
        existing_categories = {
            c.name.lower(): c
            for c in ServiceCategory.objects.filter(name__in=category_names).only(
                "id", "name"
            )
        }

        for item in services_data:
            category_name = item.pop("service_category_name", None)

            category = None
            if category_name:
                category = existing_categories.get(category_name.lower())
                if not category:
                    category = ServiceCategory.objects.create(name=category_name)
                    existing_categories[category_name.lower()] = category

            if category:
                item["service_category"] = category

            # deduplicate titles
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
