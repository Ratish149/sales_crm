# Create your views here.
from django_filters import rest_framework as django_filters
from rest_framework import filters, generics, permissions
from rest_framework.pagination import PageNumberPagination

from .models import Blog, BlogCategory, Tags
from .serializers import BlogCategorySerializer, BlogSerializer, TagsSerializer


class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class BlogCategoryListCreateView(generics.ListCreateAPIView):
    queryset = BlogCategory.objects.all()
    serializer_class = BlogCategorySerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []


class BlogCategoryRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = BlogCategory.objects.all()
    serializer_class = BlogCategorySerializer
    lookup_field = "slug"
    permission_classes = [permissions.AllowAny]
    authentication_classes = []


class BlogFilterSet(django_filters.FilterSet):
    tags = django_filters.CharFilter(field_name="tags__slug", lookup_expr="iexact")
    category = django_filters.CharFilter(
        field_name="category__slug", lookup_expr="iexact"
    )

    class Meta:
        model = Blog
        fields = ["tags", "category"]


class BlogListCreateView(generics.ListCreateAPIView):
    queryset = Blog.objects.all().order_by("-created_at")
    serializer_class = BlogSerializer
    pagination_class = CustomPagination
    filter_backends = [django_filters.DjangoFilterBackend, filters.SearchFilter]
    filterset_class = BlogFilterSet
    search_fields = ["title"]
    permission_classes = [permissions.AllowAny]
    authentication_classes = []


class BlogRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Blog.objects.all()
    serializer_class = BlogSerializer
    lookup_field = "slug"
    permission_classes = [permissions.AllowAny]
    authentication_classes = []


class TagsListCreateView(generics.ListCreateAPIView):
    queryset = Tags.objects.all()
    serializer_class = TagsSerializer
    pagination_class = CustomPagination
    permission_classes = [permissions.AllowAny]
    authentication_classes = []


class TagsRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Tags.objects.all()
    serializer_class = TagsSerializer
    lookup_field = "slug"
    permission_classes = [permissions.AllowAny]
    authentication_classes = []


# Get recent blogs api
class RecentBlogsView(generics.ListAPIView):
    queryset = Blog.objects.all().order_by("-created_at")[:5]
    serializer_class = BlogSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
