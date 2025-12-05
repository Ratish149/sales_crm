from django.urls import path

from .views import (
    BlogListCreateView,
    BlogRetrieveUpdateDestroyView,
    RecentBlogsView,
    TagsListCreateView,
    TagsRetrieveUpdateDestroyView,
)

urlpatterns = [
    path("blogs/", BlogListCreateView.as_view(), name="blog-list-create"),
    path(
        "blogs/<slug:slug>/",
        BlogRetrieveUpdateDestroyView.as_view(),
        name="blog-retrieve-update-destroy",
    ),
    path("tags/", TagsListCreateView.as_view(), name="tag-list-create"),
    path(
        "tags/<slug:slug>/",
        TagsRetrieveUpdateDestroyView.as_view(),
        name="tag-retrieve-update-destroy",
    ),
    path("recent-blogs/", RecentBlogsView.as_view(), name="recent-blogs"),
]
