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


# Columns used by BlogCategorySerializer / BlogCategorySmallSerializer
_CATEGORY_FIELDS = ("id", "name", "slug")

# Columns used by TagsSerializer / TagsSmallSerializer
_TAGS_FIELDS = ("id", "name", "slug")

# Blog own columns + FK column + related category columns via select_related
# (M2M tags are handled by prefetch_related, not listed here)
_BLOG_FIELDS = (
    "id",
    "category_id",  # FK column on Blog table
    "title",
    "slug",
    "content",
    "thumbnail_image",
    "thumbnail_image_alt_description",
    "time_to_read",
    "meta_title",
    "meta_description",
    "created_at",
    "updated_at",
    "category__id",  # pulled in by select_related
    "category__name",
    "category__slug",
)


class BlogCategoryListCreateView(generics.ListCreateAPIView):
    queryset = BlogCategory.objects.only(*_CATEGORY_FIELDS)
    serializer_class = BlogCategorySerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []


class BlogCategoryRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = BlogCategory.objects.only(*_CATEGORY_FIELDS)
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
    # select_related → 1 JOIN for category (no extra query per blog)
    # prefetch_related → 1 extra query for all tags across the page
    queryset = (
        Blog.objects
        .select_related("category")
        .prefetch_related("tags")
        .only(*_BLOG_FIELDS)
        .order_by("-created_at")
    )
    serializer_class = BlogSerializer
    pagination_class = CustomPagination
    filter_backends = [django_filters.DjangoFilterBackend, filters.SearchFilter]
    filterset_class = BlogFilterSet
    search_fields = ["title"]
    permission_classes = [permissions.AllowAny]
    authentication_classes = []


class BlogRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = (
        Blog.objects
        .select_related("category")
        .prefetch_related("tags")
        .only(*_BLOG_FIELDS)
    )
    serializer_class = BlogSerializer
    lookup_field = "slug"
    permission_classes = [permissions.AllowAny]
    authentication_classes = []


class TagsListCreateView(generics.ListCreateAPIView):
    queryset = Tags.objects.only(*_TAGS_FIELDS)
    serializer_class = TagsSerializer
    pagination_class = CustomPagination
    permission_classes = [permissions.AllowAny]
    authentication_classes = []


class TagsRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Tags.objects.only(*_TAGS_FIELDS)
    serializer_class = TagsSerializer
    lookup_field = "slug"
    permission_classes = [permissions.AllowAny]
    authentication_classes = []


# Get recent blogs api
class RecentBlogsView(generics.ListAPIView):
    """
    Returns the 5 most recent blogs.
    Slice is in get_queryset() — NOT on the class-level queryset attribute,
    because a sliced queryset is evaluated eagerly and breaks filter/paginate.
    """

    serializer_class = BlogSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get_queryset(self):
        return (
            Blog.objects
            .select_related("category")
            .prefetch_related("tags")
            .only(*_BLOG_FIELDS)
            .order_by("-created_at")[:5]
        )
