# Create your views here.
from django_filters import rest_framework as django_filters
from rest_framework import filters, generics
from rest_framework.pagination import PageNumberPagination

from .models import Blog, Tags
from .serializers import BlogSerializer, TagsSerializer


class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class BlogFilterSet(django_filters.FilterSet):
    tags = django_filters.CharFilter(field_name="tags__slug", lookup_expr="iexact")

    class Meta:
        model = Blog
        fields = ["tags"]


class BlogListCreateView(generics.ListCreateAPIView):
    queryset = Blog.objects.all().order_by("-created_at")
    serializer_class = BlogSerializer
    pagination_class = CustomPagination
    filter_backends = [django_filters.DjangoFilterBackend, filters.SearchFilter]
    filterset_class = BlogFilterSet
    search_fields = ["title"]


class BlogRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Blog.objects.all()
    serializer_class = BlogSerializer
    lookup_field = "slug"


class TagsListCreateView(generics.ListCreateAPIView):
    queryset = Tags.objects.all()
    serializer_class = TagsSerializer
    pagination_class = CustomPagination


class TagsRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Tags.objects.all()
    serializer_class = TagsSerializer
    lookup_field = "slug"


# Get recent blogs api
class RecentBlogsView(generics.ListAPIView):
    queryset = Blog.objects.all().order_by("-created_at")[:5]
    serializer_class = BlogSerializer
