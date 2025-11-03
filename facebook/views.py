from rest_framework import generics, response, status

from .models import Conversation, Facebook
from .serializers import (
    ConversationMessageSerializer,
    ConversationSerializer,
    FacebookSerializer,
)
from .utils import sync_conversations_from_facebook, sync_messages_for_conversation


class FacebookListCreateView(generics.ListCreateAPIView):
    queryset = Facebook.objects.filter(is_enabled=True)
    serializer_class = FacebookSerializer
    # permission_classes = [IsAuthenticated]


class FacebookRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Facebook.objects.all()
    serializer_class = FacebookSerializer


class ConversationListAPIView(generics.ListAPIView):
    serializer_class = ConversationSerializer

    def get_queryset(self):
        # Check if frontend provided a page_id
        page_id = self.request.query_params.get("page_id")

        if page_id:
            try:
                page = Facebook.objects.get(page_id=page_id, is_enabled=True)
                # Sync conversations only for this page
                sync_conversations_from_facebook(page)
                return Conversation.objects.filter(page=page).order_by("-updated_time")
            except Facebook.DoesNotExist:
                return (
                    Conversation.objects.none()
                )  # return empty queryset if page not found
        else:
            # If no page_id, fallback to all enabled pages
            pages = Facebook.objects.filter(is_enabled=True)
            for page in pages:
                sync_conversations_from_facebook(page)
            return Conversation.objects.all().order_by("-updated_time")


class ConversationMessageAPIView(generics.RetrieveAPIView):
    serializer_class = ConversationMessageSerializer
    lookup_field = "conversation_id"
    queryset = Conversation.objects.all()

    def get(self, request, *args, **kwargs):
        conversation = self.get_object()
        refresh = request.query_params.get("refresh") == "true"
        result = sync_messages_for_conversation(conversation, force_refresh=refresh)
        data = self.serializer_class(conversation).data
        return response.Response(
            {"result": result, "conversation": data}, status=status.HTTP_200_OK
        )
