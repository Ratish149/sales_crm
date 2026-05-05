from django.urls import path

from .views import (
    DashboardStatsSummaryAPIView,
    RecentActivityAPIView,
    RecentUsersAPIView,
    UserRegistrationDailyAPIView,
)

urlpatterns = [
    path(
        "dashboard/summary/",
        DashboardStatsSummaryAPIView.as_view(),
        name="dashboard-stats-summary",
    ),
    path(
        "dashboard/recent-activities/",
        RecentActivityAPIView.as_view(),
        name="dashboard-recent-activities",
    ),
    path(
        "dashboard/recent-users/",
        RecentUsersAPIView.as_view(),
        name="dashboard-recent-users",
    ),
    path(
        "dashboard/user-registrations/",
        UserRegistrationDailyAPIView.as_view(),
        name="dashboard-user-registrations",
    ),
]
