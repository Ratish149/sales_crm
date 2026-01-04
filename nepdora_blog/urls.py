from django.urls import path

from .views import (
    BlogCategoryListCreateView,
    BlogCategoryRetrieveUpdateDestroyView,
    BlogListCreateView,
    BlogRetrieveUpdateDestroyView,
    RecentBlogsView,
    TagsListCreateView,
    TagsRetrieveUpdateDestroyView,
)

urlpatterns = [
    path(
        "nepdora-blog-categories/",
        BlogCategoryListCreateView.as_view(),
        name="blog-category-list-create",
    ),
    path(
        "nepdora-blog-categories/<slug:slug>/",
        BlogCategoryRetrieveUpdateDestroyView.as_view(),
        name="blog-category-retrieve-update-destroy",
    ),
    path("nepdora-blogs/", BlogListCreateView.as_view(), name="blog-list-create"),
    path(
        "nepdora-blogs/<slug:slug>/",
        BlogRetrieveUpdateDestroyView.as_view(),
        name="blog-retrieve-update-destroy",
    ),
    path("nepdora-tags/", TagsListCreateView.as_view(), name="tag-list-create"),
    path(
        "nepdora-tags/<slug:slug>/",
        TagsRetrieveUpdateDestroyView.as_view(),
        name="tag-retrieve-update-destroy",
    ),
    path("nepdora-recent-blogs/", RecentBlogsView.as_view(), name="recent-blogs"),
]
