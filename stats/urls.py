from django.urls import path
from .views import UnreadCountView, StatsView

urlpatterns = [
    path("unread-counts/", UnreadCountView.as_view(), name="unread-counts"),
    path("stats/", StatsView.as_view(), name="stats"),
]
