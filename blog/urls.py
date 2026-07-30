from django.urls import path

from .views import (
    BlogBulkCreateView,
    BlogCategoryListCreateView,
    BlogCategoryRetrieveUpdateDestroyView,
    BlogListCreateView,
    BlogRetrieveUpdateDestroyView,
    RecentBlogsView,
    TagsListCreateView,
    TagsRetrieveUpdateDestroyView,
)

urlpatterns = [
    path("categories/", BlogCategoryListCreateView.as_view(), name="blog-category-list-create"),
    path(
        "categories/<slug:slug>/",
        BlogCategoryRetrieveUpdateDestroyView.as_view(),
        name="blog-category-retrieve-update-destroy",
    ),
    path("blogs/", BlogListCreateView.as_view(), name="blog-list-create"),
    path(
        "blogs/<slug:slug>/",
        BlogRetrieveUpdateDestroyView.as_view(),
        name="blog-retrieve-update-destroy",
    ),
    path(
        "blogs-bulk-create/",
        BlogBulkCreateView.as_view(),
        name="blog-bulk-create",
    ),
    path("tags/", TagsListCreateView.as_view(), name="tag-list-create"),
    path(
        "tags/<slug:slug>/",
        TagsRetrieveUpdateDestroyView.as_view(),
        name="tag-retrieve-update-destroy",
    ),
    path("recent-blogs/", RecentBlogsView.as_view(), name="recent-blogs"),
]
