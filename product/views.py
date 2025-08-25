from django.shortcuts import render
from rest_framework import generics, filters
from .models import Product, ProductImage, SubCategory, Category
from .serializers import ProductSerializer, ProductSmallSerializer, ProductImageSerializer, SubCategorySerializer, CategorySerializer, SubCategoryDetailSerializer
from rest_framework.pagination import PageNumberPagination
from django_filters import rest_framework as django_filters

# Create your views here.


class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class CategoryListCreateView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    pagination_class = CustomPagination


class CategoryRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = 'slug'


class SubCategoryListCreateView(generics.ListCreateAPIView):
    queryset = SubCategory.objects.all()
    serializer_class = SubCategorySerializer
    pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return SubCategorySerializer
        return SubCategoryDetailSerializer


class SubCategoryRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = SubCategory.objects.all()
    serializer_class = SubCategorySerializer
    lookup_field = 'slug'

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return SubCategorySerializer
        return SubCategoryDetailSerializer


class ProductImageListCreateView(generics.ListCreateAPIView):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer


class ProductImageRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer


class ProductFilterSet(django_filters.FilterSet):
    category = django_filters.CharFilter(
        field_name='category__slug', lookup_expr='iexact')
    sub_category = django_filters.CharFilter(
        field_name='sub_category__slug', lookup_expr='iexact')

    class Meta:
        model = Product
        fields = ['category', 'sub_category']


class ProductListCreateView(generics.ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    pagination_class = CustomPagination
    filter_backends = [
        django_filters.DjangoFilterBackend, filters.SearchFilter]
    filterset_class = ProductFilterSet
    search_fields = ['name']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProductSerializer
        return ProductSmallSerializer


class ProductRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    lookup_field = 'slug'
