from django.urls import path

from .views import (
    TeamMemberCategoryListCreateView,
    TeamMemberCategoryRetrieveUpdateDestroyView,
    TeamMemberListCreateView,
    TeamMemberRetrieveUpdateDestroyView,
)

urlpatterns = [
    path(
        "team-member-category/",
        TeamMemberCategoryListCreateView.as_view(),
        name="team-member-category-list-create",
    ),
    path(
        "team-member-category/<int:pk>/",
        TeamMemberCategoryRetrieveUpdateDestroyView.as_view(),
        name="team-member-category-retrieve-update-destroy",
    ),
    path(
        "team-member/",
        TeamMemberListCreateView.as_view(),
        name="team-member-list-create",
    ),
    path(
        "team-member/<int:pk>/",
        TeamMemberRetrieveUpdateDestroyView.as_view(),
        name="team-member-retrieve-update-destroy",
    ),
]
