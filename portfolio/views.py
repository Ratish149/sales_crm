from django.db import transaction
from django_filters import rest_framework as django_filters
from rest_framework import filters, generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from sales_crm.authentication import TenantJWTAuthentication

from .models import Portfolio, PortfolioCategory, PortfolioImage, PortfolioTags
from .serializers import (
    BulkCreatePortfolioSerializer,
    PortfolioCategorySerializer,
    PortfolioDetailSerializer,
    PortfolioImageSerializer,
    PortfolioListSerializer,
    PortfolioSerializer,
    PortfolioTagsSerializer,
)


class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


# Create your views here.


class PortfolioCategoryListCreateAPIView(generics.ListCreateAPIView):
    queryset = PortfolioCategory.objects.all()
    serializer_class = PortfolioCategorySerializer


class PortfolioCategoryRetrieveUpdateDestroyAPIView(
    generics.RetrieveUpdateDestroyAPIView
):
    queryset = PortfolioCategory.objects.all()
    serializer_class = PortfolioCategorySerializer


class PortfolioTagsListCreateAPIView(generics.ListCreateAPIView):
    queryset = PortfolioTags.objects.all()
    serializer_class = PortfolioTagsSerializer


class PortfolioTagsRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PortfolioTags.objects.all()
    serializer_class = PortfolioTagsSerializer


class PortfolioFilterSet(django_filters.FilterSet):
    category = django_filters.CharFilter(field_name="category", lookup_expr="exact")
    tags = django_filters.CharFilter(field_name="tags", lookup_expr="exact")

    class Meta:
        model = Portfolio
        fields = ["category", "tags"]


class PortfolioListCreateAPIView(generics.ListCreateAPIView):
    queryset = Portfolio.objects.all().order_by("-created_at")
    serializer_class = PortfolioSerializer
    filter_backends = [django_filters.DjangoFilterBackend, filters.SearchFilter]
    filterset_class = PortfolioFilterSet
    search_fields = ["title"]
    pagination_class = CustomPagination

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
            return PortfolioListSerializer
        return PortfolioSerializer


class PortfolioRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Portfolio.objects.all()
    serializer_class = PortfolioSerializer
    lookup_field = "slug"

    def get_authenticators(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [TenantJWTAuthentication()]
        return []

    def get_permissions(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.request.method == "GET":
            return PortfolioDetailSerializer
        return PortfolioSerializer


class PortfolioImageListCreateAPIView(generics.ListCreateAPIView):
    queryset = PortfolioImage.objects.all()
    serializer_class = PortfolioImageSerializer

    def get_authenticators(self):
        if self.request.method == "POST":
            return [TenantJWTAuthentication()]
        return []

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return super().get_permissions()


class PortfolioImageRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PortfolioImage.objects.all()
    serializer_class = PortfolioImageSerializer

    def get_authenticators(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [TenantJWTAuthentication()]
        return []

    def get_permissions(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [IsAuthenticated()]
        return super().get_permissions()


class PortfolioBulkCreateView(APIView):
    """
    POST /api/portfolio-bulk-create/

    Accepts a JSON body with a `portfolios` list and creates all of them
    inside a single database transaction.
    """

    authentication_classes = [TenantJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = BulkCreatePortfolioSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        portfolios_data = serializer.validated_data["portfolios"]
        created_portfolios = []

        for item in portfolios_data:
            cat_name = item.pop("category_name", None)
            tag_names = item.pop("tag_names", [])
            # Resolve category
            category = None
            if cat_name:
                category = PortfolioCategory.objects.filter(
                    name__icontains=cat_name
                ).first()
                if not category:
                    category = PortfolioCategory.objects.create(name=cat_name)

            if category:
                item["category"] = category

            # Deduplicate titles
            title = item["title"]
            if Portfolio.objects.filter(title=title).exists():
                suffix = 1
                while Portfolio.objects.filter(title=f"{title} ({suffix})").exists():
                    suffix += 1
                item["title"] = f"{title} ({suffix})"

            portfolio = Portfolio.objects.create(**item)

            # Resolve tags
            tag_objects = set()
            if tag_names:
                for name in tag_names:
                    tag = PortfolioTags.objects.filter(name__icontains=name).first()
                    if not tag:
                        tag = PortfolioTags.objects.create(name=name)
                    tag_objects.add(tag)

            if tag_objects:
                portfolio.tags.set(list(tag_objects))

            created_portfolios.append(portfolio)

        response_data = PortfolioSerializer(created_portfolios, many=True).data
        return Response(
            {"created": len(created_portfolios), "portfolios": response_data},
            status=status.HTTP_201_CREATED,
        )
