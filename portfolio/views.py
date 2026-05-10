from django.db import transaction
from django.db.models import Prefetch
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


# reusable querysets
CATEGORY_QS = PortfolioCategory.objects.only(
    "id", "name", "slug", "created_at", "updated_at"
)
TAGS_QS = PortfolioTags.objects.only("id", "name", "slug", "created_at", "updated_at")
IMAGE_QS = PortfolioImage.objects.only(
    "id", "portfolio_id", "image", "alt_description", "created_at", "updated_at"
)

PORTFOLIO_OPTIMIZED_QS = (
    Portfolio.objects
    .select_related("category")
    .prefetch_related(
        Prefetch("tags", queryset=TAGS_QS),
        Prefetch("images", queryset=IMAGE_QS),
    )
    .only(
        "id",
        "title",
        "slug",
        "content",
        "thumbnail_image",
        "thumbnail_image_alt_description",
        "category_id",  # FK column, needed by select_related
        "category__id",
        "category__name",
        "category__slug",
        "category__created_at",
        "category__updated_at",
        "project_url",
        "github_url",
        "meta_title",
        "meta_description",
        "created_at",
        "updated_at",
    )
    .order_by("-created_at")
)


class PortfolioCategoryListCreateAPIView(generics.ListCreateAPIView):
    queryset = CATEGORY_QS
    serializer_class = PortfolioCategorySerializer


class PortfolioCategoryRetrieveUpdateDestroyAPIView(
    generics.RetrieveUpdateDestroyAPIView
):
    queryset = CATEGORY_QS
    serializer_class = PortfolioCategorySerializer


class PortfolioTagsListCreateAPIView(generics.ListCreateAPIView):
    queryset = TAGS_QS
    serializer_class = PortfolioTagsSerializer


class PortfolioTagsRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TAGS_QS
    serializer_class = PortfolioTagsSerializer


class PortfolioFilterSet(django_filters.FilterSet):
    category = django_filters.CharFilter(field_name="category", lookup_expr="exact")
    tags = django_filters.CharFilter(field_name="tags", lookup_expr="exact")

    class Meta:
        model = Portfolio
        fields = ["category", "tags"]


class PortfolioListCreateAPIView(generics.ListCreateAPIView):
    queryset = PORTFOLIO_OPTIMIZED_QS
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
    queryset = PORTFOLIO_OPTIMIZED_QS
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
    queryset = IMAGE_QS
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
    queryset = IMAGE_QS
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
    authentication_classes = [TenantJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = BulkCreatePortfolioSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        portfolios_data = serializer.validated_data["portfolios"]
        created_portfolios = []

        # batch-fetch all matching categories and tags in one query each
        cat_names = [
            i["category_name"] for i in portfolios_data if i.get("category_name")
        ]
        tag_names_flat = [n for i in portfolios_data for n in i.get("tag_names", [])]

        existing_categories = {
            c.name.lower(): c
            for c in PortfolioCategory.objects.filter(name__in=cat_names).only(
                "id", "name"
            )
        }
        existing_tags = {
            t.name.lower(): t
            for t in PortfolioTags.objects.filter(name__in=tag_names_flat).only(
                "id", "name"
            )
        }

        for item in portfolios_data:
            cat_name = item.pop("category_name", None)
            tag_names = item.pop("tag_names", [])

            category = None
            if cat_name:
                category = existing_categories.get(cat_name.lower())
                if not category:
                    category = PortfolioCategory.objects.create(name=cat_name)
                    existing_categories[cat_name.lower()] = category
            if category:
                item["category"] = category

            # deduplicate titles — two queries per conflict, acceptable for bulk
            title = item["title"]
            if Portfolio.objects.filter(title=title).exists():
                suffix = 1
                while Portfolio.objects.filter(title=f"{title} ({suffix})").exists():
                    suffix += 1
                item["title"] = f"{title} ({suffix})"

            portfolio = Portfolio.objects.create(**item)

            tag_objects = set()
            for name in tag_names:
                tag = existing_tags.get(name.lower())
                if not tag:
                    tag = PortfolioTags.objects.create(name=name)
                    existing_tags[name.lower()] = tag
                tag_objects.add(tag)

            if tag_objects:
                portfolio.tags.set(list(tag_objects))

            created_portfolios.append(portfolio)

        response_data = PortfolioSerializer(created_portfolios, many=True).data
        return Response(
            {"created": len(created_portfolios), "portfolios": response_data},
            status=status.HTTP_201_CREATED,
        )
