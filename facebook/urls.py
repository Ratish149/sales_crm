from django.urls import path

from .views import (
    ConversationListAPIView,
    ConversationMessageAPIView,
    FacebookListCreateView,
    FacebookRetrieveUpdateDestroyView,
    facebook_webhook,
)

urlpatterns = [
    path("facebook/", FacebookListCreateView.as_view(), name="facebook-list-create"),
    path(
        "facebook/<int:pk>/",
        FacebookRetrieveUpdateDestroyView.as_view(),
        name="facebook-retrieve-update-destroy",
    ),
    path("conversations/", ConversationListAPIView.as_view(), name="conversation-list"),
    path(
        "conversation-messages/<str:conversation_id>/",
        ConversationMessageAPIView.as_view(),
        name="conversation-messages",
    ),
    path("facebook/webhook/", facebook_webhook, name="facebook-webhook"),
]
