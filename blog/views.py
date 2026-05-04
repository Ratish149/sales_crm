# Create your views here.
from django.db import transaction
from django_filters import rest_framework as django_filters
from rest_framework import filters, generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from sales_crm.authentication import TenantJWTAuthentication

from .models import Blog, Tags
from .serializers import BlogSerializer, BulkCreateBlogSerializer, TagsSerializer


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

    def get_authenticators(self):
        if self.request.method == "POST":
            return [TenantJWTAuthentication()]
        return []  # No authentication for GET

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return super().get_permissions()


class BlogRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Blog.objects.all()
    serializer_class = BlogSerializer
    lookup_field = "slug"

    def get_authenticators(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [TenantJWTAuthentication()]
        return []

    def get_permissions(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [IsAuthenticated()]
        return super().get_permissions()


class TagsListCreateView(generics.ListCreateAPIView):
    queryset = Tags.objects.all()
    serializer_class = TagsSerializer
    pagination_class = CustomPagination


class TagsRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Tags.objects.all()
    serializer_class = TagsSerializer
    lookup_field = "slug"

    def get_authenticators(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [TenantJWTAuthentication()]
        return []

    def get_permissions(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [IsAuthenticated()]
        return super().get_permissions()


# Get recent blogs api
class RecentBlogsView(generics.ListAPIView):
    queryset = Blog.objects.all().order_by("-created_at")[:5]
    serializer_class = BlogSerializer


class BlogBulkCreateView(APIView):
    """
    POST /api/blogs/bulk-create/

    Accepts a JSON body with a `blogs` list and creates all of them
    inside a single database transaction.

    Request body example:
    {
      "blogs": [
        {
          "title": "Blog One",
          "content": "<p>...</p>",
          "time_to_read": "4 min read",
          "meta_title": "...",
          "meta_description": "...",
          "tag_ids": [1, 2]
        },
        { ... }
      ]
    }

    Response on success (201):
    {
      "created": 3,
      "blogs": [ <BlogSerializer data for each created blog> ]
    }
    """

    authentication_classes = [TenantJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = BulkCreateBlogSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        blogs_data = serializer.validated_data["blogs"]
        created_blogs = []

        for item in blogs_data:
            tag_names = item.pop("tag_names", [])

            # Deduplicate titles
            title = item["title"]
            if Blog.objects.filter(title=title).exists():
                suffix = 1
                while Blog.objects.filter(title=f"{title} ({suffix})").exists():
                    suffix += 1
                item["title"] = f"{title} ({suffix})"

            blog = Blog.objects.create(**item)

            tag_objects = set()
            if tag_names:
                for name in tag_names:
                    # Case-insensitive lookup using icontains
                    tag = Tags.objects.filter(name__icontains=name).first()
                    if not tag:
                        tag = Tags.objects.create(name=name)
                    tag_objects.add(tag)

            if tag_objects:
                blog.tags.set(tag_objects)

            created_blogs.append(blog)

        response_data = BlogSerializer(created_blogs, many=True).data
        return Response(
            {"created": len(created_blogs), "blogs": response_data},
            status=status.HTTP_201_CREATED,
        )
