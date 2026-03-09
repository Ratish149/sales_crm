from django.urls import path
from .views import UnreadCountView

urlpatterns = [
    path("unread-counts/", UnreadCountView.as_view(), name="unread-counts"),
]
