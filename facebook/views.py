import json

from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics, response, status

from .models import Conversation, Facebook
from .serializers import (
    ConversationMessageSerializer,
    ConversationSerializer,
    FacebookSerializer,
)
from .utils import sync_conversations_from_facebook, sync_messages_for_conversation

VERIFY_TOKEN = "secret123"  # 🔑 same as you’ll set in Facebook Developer dashboard


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


@csrf_exempt
def facebook_webhook(request):
    if request.method == "GET":
        # ✅ Facebook verification step
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")

        if mode == "subscribe" and token == VERIFY_TOKEN:
            print("✅ Webhook verified!")
            return HttpResponse(challenge)
        else:
            print("❌ Verification failed!")
            return HttpResponse("Verification token mismatch", status=403)

    elif request.method == "POST":
        # ✅ Handle incoming messages
        payload = json.loads(request.body.decode("utf-8"))
        print("📩 Incoming webhook payload:", json.dumps(payload, indent=2))

        entry = payload.get("entry", [])
        for e in entry:
            messaging = e.get("messaging", [])
            for msg_event in messaging:
                sender_id = msg_event["sender"]["id"]
                recipient_id = msg_event["recipient"]["id"]
                timestamp = msg_event.get("timestamp")
                message = msg_event.get("message", {}).get("text", "")

                # Save to DB
                try:
                    page = Facebook.objects.filter(page_id=recipient_id).first()
                    if not page:
                        continue

                    conversation, _ = Conversation.objects.get_or_create(
                        conversation_id=sender_id,
                        defaults={
                            "page": page,
                            "participants": [
                                {"sender": sender_id, "recipient": recipient_id}
                            ],
                            "messages": [],
                        },
                    )

                    conversation.messages.append(
                        {
                            "sender_id": sender_id,
                            "recipient_id": recipient_id,
                            "message": message,
                            "timestamp": timestamp,
                        }
                    )
                    conversation.snippet = message
                    conversation.updated_time = timezone.now()
                    conversation.last_synced = timezone.now()
                    conversation.save()

                except Exception as e:
                    print("Error saving message:", e)

        return JsonResponse({"status": "ok"})

    return HttpResponse(status=405)
