from django.urls import path

from .views import (
    IssueCategoryListCreateAPIView,
    IssueCategoryRetrieveUpdateDestroyAPIView,
    IssueListCreateAPIView,
    IssueRetrieveUpdateDestroyAPIView,
)

urlpatterns = [
    path("issue/", IssueListCreateAPIView.as_view(), name="issue-list-create"),
    path(
        "issue/<int:pk>/",
        IssueRetrieveUpdateDestroyAPIView.as_view(),
        name="issue-retrieve-update-destroy",
    ),
    path(
        "issue-category/",
        IssueCategoryListCreateAPIView.as_view(),
        name="issue-category-list-create",
    ),
    path(
        "issue-category/<int:pk>/",
        IssueCategoryRetrieveUpdateDestroyAPIView.as_view(),
        name="issue-category-retrieve-update-destroy",
    ),
]
