from django.db import transaction
from django.db.models import Prefetch
from django_filters import rest_framework as django_filters
from rest_framework import filters, generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from sales_crm.authentication import TenantJWTAuthentication

from .filters import BlogCategoryFilterSet, BlogFilterSet
from .models import Blog, BlogCategory, Tags
from .serializers import (
    BlogCategorySerializer,
    BlogSerializer,
    BulkCreateBlogSerializer,
    TagsSerializer,
)


class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class BlogCategoryListCreateView(generics.ListCreateAPIView):
    queryset = BlogCategory.objects.only(
        "id", "name", "slug", "created_at", "updated_at"
    ).order_by("name")
    serializer_class = BlogCategorySerializer
    pagination_class = CustomPagination
    filter_backends = [django_filters.DjangoFilterBackend, filters.SearchFilter]
    filterset_class = BlogCategoryFilterSet
    search_fields = ["name"]

    def get_authenticators(self):
        if self.request.method == "POST":
            return [TenantJWTAuthentication()]
        return []

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return super().get_permissions()


class BlogCategoryRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = BlogCategory.objects.only(
        "id", "name", "slug", "created_at", "updated_at"
    )
    serializer_class = BlogCategorySerializer
    lookup_field = "slug"

    def get_authenticators(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [TenantJWTAuthentication()]
        return []

    def get_permissions(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [IsAuthenticated()]
        return super().get_permissions()


class BlogListCreateView(generics.ListCreateAPIView):
    queryset = (
        Blog.objects.select_related("category")
        .prefetch_related(
            Prefetch("tags", queryset=Tags.objects.only("id", "name", "slug"))
        )
        .only(
            "id",
            "category__id",
            "category__name",
            "category__slug",
            "title",
            "slug",
            "content",
            "thumbnail_image",
            "thumbnail_image_alt_description",
            "author",
            "time_to_read",
            "meta_title",
            "meta_description",
            "is_featured",
            "created_at",
            "updated_at",
        )
        .order_by("-created_at")
    )
    serializer_class = BlogSerializer
    pagination_class = CustomPagination
    filter_backends = [django_filters.DjangoFilterBackend, filters.SearchFilter]
    filterset_class = BlogFilterSet
    search_fields = ["title", "author"]

    def get_authenticators(self):
        if self.request.method == "POST":
            return [TenantJWTAuthentication()]
        return []

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return super().get_permissions()


class BlogRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = (
        Blog.objects.select_related("category")
        .prefetch_related(
            Prefetch("tags", queryset=Tags.objects.only("id", "name", "slug"))
        )
        .only(
            "id",
            "category__id",
            "category__name",
            "category__slug",
            "title",
            "slug",
            "content",
            "thumbnail_image",
            "thumbnail_image_alt_description",
            "author",
            "time_to_read",
            "meta_title",
            "meta_description",
            "is_featured",
            "created_at",
            "updated_at",
        )
    )
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
    queryset = Tags.objects.only("id", "name", "slug", "created_at", "updated_at")
    serializer_class = TagsSerializer
    pagination_class = CustomPagination


class TagsRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Tags.objects.only("id", "name", "slug", "created_at", "updated_at")
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


class RecentBlogsView(generics.ListAPIView):
    queryset = (
        Blog.objects.select_related("category")
        .prefetch_related(
            Prefetch("tags", queryset=Tags.objects.only("id", "name", "slug"))
        )
        .only(
            "id",
            "category__id",
            "category__name",
            "category__slug",
            "title",
            "slug",
            "content",
            "thumbnail_image",
            "thumbnail_image_alt_description",
            "author",
            "time_to_read",
            "meta_title",
            "meta_description",
            "is_featured",
            "created_at",
            "updated_at",
        )
        .order_by("-created_at")[:5]
    )
    serializer_class = BlogSerializer


class BlogBulkCreateView(APIView):
    """POST /api/blogs-bulk-create/

    Accepts a JSON body with a `blogs` list and creates all of them inside a
    single database transaction.
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
            category_name = item.pop("category", None)

            if category_name:
                category = BlogCategory.objects.filter(
                    name__icontains=category_name
                ).first()
                if not category:
                    category = BlogCategory.objects.create(name=category_name)
                item["category"] = category

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
                    tag = Tags.objects.filter(name__icontains=name).first()
                    if not tag:
                        tag = Tags.objects.create(name=name)
                    tag_objects.add(tag)

            if tag_objects:
                blog.tags.set(tag_objects)

            created_blogs.append(blog)

        response_blogs = (
            Blog.objects.filter(id__in=[b.id for b in created_blogs])
            .select_related("category")
            .prefetch_related(
                Prefetch("tags", queryset=Tags.objects.only("id", "name", "slug"))
            )
            .only(
                "id",
                "category__id",
                "category__name",
                "category__slug",
                "title",
                "slug",
                "content",
                "thumbnail_image",
                "thumbnail_image_alt_description",
                "author",
                "time_to_read",
                "meta_title",
                "meta_description",
                "is_featured",
                "created_at",
                "updated_at",
            )
        )
        response_data = BlogSerializer(response_blogs, many=True).data
        return Response(
            {"created": len(created_blogs), "blogs": response_data},
            status=status.HTTP_201_CREATED,
        )
