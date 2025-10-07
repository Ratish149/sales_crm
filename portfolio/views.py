from django_filters import rest_framework as django_filters
from rest_framework import filters, generics

from .models import Portfolio, PortfolioCategory, PortfolioTags
from .serializers import (
    PortfolioCategorySerializer,
    PortfolioDetailSerializer,
    PortfolioListSerializer,
    PortfolioSerializer,
    PortfolioTagsSerializer,
)

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
    queryset = Portfolio.objects.all()
    serializer_class = PortfolioSerializer
    filter_backends = [django_filters.DjangoFilterBackend, filters.SearchFilter]
    filterset_class = PortfolioFilterSet
    search_fields = ["title"]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return PortfolioListSerializer
        return PortfolioSerializer


class PortfolioRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Portfolio.objects.all()
    serializer_class = PortfolioSerializer
    lookup_field = "slug"

    def get_serializer_class(self):
        if self.request.method == "GET":
            return PortfolioDetailSerializer
        return PortfolioSerializer
