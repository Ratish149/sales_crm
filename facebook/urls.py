from django.urls import path

from .views import (
    ConversationListAPIView,
    ConversationMessageAPIView,
    FacebookListCreateView,
    FacebookRetrieveUpdateDestroyView,
    SyncPageData,
    TenantFacebookWebhookMessageView,
)

urlpatterns = [
    path("facebook/", FacebookListCreateView.as_view(), name="facebook-list-create"),
    path(
        "facebook/<int:pk>/",
        FacebookRetrieveUpdateDestroyView.as_view(),
        name="facebook-retrieve-update-destroy",
    ),
    path(
        "conversations/<str:page_id>/",
        ConversationListAPIView.as_view(),
        name="conversation-list",
    ),
    path(
        "conversation-messages/<str:conversation_id>/",
        ConversationMessageAPIView.as_view(),
        name="conversation-messages",
    ),
    path(
        "facebook/tenant-webhook/",
        TenantFacebookWebhookMessageView.as_view(),
        name="tenant-webhook",
    ),
    path(
        "sync-page/<str:page_id>/",
        SyncPageData.as_view(),
        name="sync-page-data",
    ),
]
