import logging
from datetime import datetime

import requests
from django.utils import timezone
from django_tenants.utils import get_public_schema_name, schema_context
from rest_framework import generics, response, status
from rest_framework.response import Response
from rest_framework.views import APIView

from tenants.models import FacebookPageTenantMap

from .models import Conversation, Facebook
from .serializers import (
    ConversationMessageSerializer,
    ConversationSerializer,
    FacebookSerializer,
)

logger = logging.getLogger(__name__)


class FacebookListCreateView(generics.ListCreateAPIView):
    queryset = Facebook.objects.all()
    serializer_class = FacebookSerializer
    # permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        # Get the current tenant
        tenant = self.request.tenant

        # Save the Facebook instance first
        facebook_instance = serializer.save()

        # Create the mapping in the public schema
        with schema_context(get_public_schema_name()):
            # Check if mapping already exists
            if not FacebookPageTenantMap.objects.filter(
                page_id=facebook_instance.page_id
            ).exists():
                FacebookPageTenantMap.objects.create(
                    page_id=facebook_instance.page_id,
                    page_name=facebook_instance.page_name,
                    tenant=tenant,
                )
                print(
                    f"Created FacebookPageTenantMap for page {facebook_instance.page_name} -> tenant {tenant.schema_name}"
                )

        return facebook_instance


class FacebookRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Facebook.objects.all()
    serializer_class = FacebookSerializer

    def perform_destroy(self, instance):
        # Delete the FacebookPageTenantMap in public schema before deleting the instance
        with schema_context(get_public_schema_name()):
            FacebookPageTenantMap.objects.filter(page_id=instance.page_id).delete()
            print(f"Deleted FacebookPageTenantMap for page {instance.page_name}")

        # Now delete the Facebook instance
        instance.delete()


class ConversationListAPIView(generics.ListAPIView):
    serializer_class = ConversationSerializer

    def get_queryset(self, page_id=None):
        if page_id:
            try:
                page = Facebook.objects.get(page_id=page_id, is_enabled=True)
                return Conversation.objects.filter(page=page).order_by("-updated_time")
            except Facebook.DoesNotExist:
                return (
                    Conversation.objects.none()
                )  # return empty queryset if page not found
        else:
            # If no page_id, fallback to all enabled pages
            return Conversation.objects.all().order_by("-updated_time")


class ConversationMessageAPIView(generics.RetrieveAPIView):
    serializer_class = ConversationMessageSerializer
    lookup_field = "conversation_id"
    queryset = Conversation.objects.all()

    def get(self, request, *args, **kwargs):
        conversation = self.get_object()
        data = self.serializer_class(conversation).data
        return response.Response({"conversation": data}, status=status.HTTP_200_OK)


class TenantFacebookWebhookMessageView(APIView):
    """
    Runs inside each tenant.
    Receives forwarded webhook payloads and stores messages in Conversation in the given JSON format.
    """

    def post(self, request, *args, **kwargs):
        payload = request.data
        logger.info(f"📨 Tenant webhook received: {payload}")

        for entry in payload.get("entry", []):
            page_id = entry.get("id")
            messaging_events = entry.get("messaging", [])

            if not page_id or not messaging_events:
                continue

            # Step 1: find Facebook page
            try:
                page = Facebook.objects.get(page_id=page_id)
            except Facebook.DoesNotExist:
                logger.warning(f"⚠️ No Facebook page found for page_id={page_id}")
                continue

            # Step 2: handle each message
            for event in messaging_events:
                message = event.get("message")
                sender_info = event.get("sender", {})
                recipient_info = event.get("recipient", {})

                if not message:
                    continue

                sender_id = sender_info.get("id")
                recipient_id = recipient_info.get("id")
                msg_text = message.get("text", "")
                msg_id = message.get("mid", "")
                timestamp = event.get("timestamp", None)

                # Step 3: Check if conversation already exists
                convo = Conversation.objects.filter(
                    page=page, participants__contains=[{"id": sender_id}]
                ).first()

                if convo:
                    # Existing conversation, avoid Graph API call
                    conv_id = convo.conversation_id
                    sender_name = next(
                        (p["name"] for p in convo.participants if p["id"] == sender_id),
                        sender_id,
                    )
                    print("✅ Existing conversation detected")
                    logger.info(
                        f"✅ Existing conversation detected for sender {sender_id}"
                    )
                else:
                    # New sender, call Graph API to get official conversation ID and name
                    conv_id = f"{sender_id}-{recipient_id}"  # fallback
                    sender_name = sender_id
                    print("📞 New user → calling conversation API")
                    try:
                        conv_url = f"https://graph.facebook.com/v20.0/{page.page_id}/conversations"
                        params = {
                            "access_token": page.page_access_token,
                            "fields": "participants,id",
                        }
                        while conv_url:
                            r = requests.get(conv_url, params=params)
                            data = r.json()
                            for conv in data.get("data", []):
                                participant_ids = [
                                    p["id"]
                                    for p in conv.get("participants", {}).get(
                                        "data", []
                                    )
                                ]
                                if sender_id in participant_ids:
                                    conv_id = conv["id"]
                                    for p in conv.get("participants", {}).get(
                                        "data", []
                                    ):
                                        if p["id"] == sender_id:
                                            sender_name = p.get("name", sender_id)
                                            break
                                    break
                            if conv_id != f"{sender_id}-{recipient_id}":
                                break
                            conv_url = data.get("paging", {}).get("next")
                            params = {}
                        logger.info(
                            f"✅ New conversation created for sender {sender_id} with conv_id {conv_id}"
                        )
                    except Exception as e:
                        logger.warning(
                            f"⚠️ Could not fetch official conversation ID: {e}"
                        )

                # Step 4: Build message JSON
                message_json = {
                    "id": msg_id,
                    "from": {
                        "id": sender_id,
                        "name": sender_name,
                        "email": f"{sender_id}@facebook.com",
                    },
                    "message": msg_text,
                    "created_time": (
                        datetime.utcfromtimestamp(timestamp / 1000).isoformat()
                        + "+0000"
                        if timestamp
                        else datetime.utcnow().isoformat() + "+0000"
                    ),
                }

                # Step 5: Create or update conversation
                if convo is None:
                    convo, _ = Conversation.objects.get_or_create(
                        conversation_id=conv_id,
                        page=page,
                        defaults={
                            "participants": [{"id": sender_id, "name": sender_name}],
                            "messages": [],
                        },
                    )

                # Step 6: Avoid duplicate messages
                existing_ids = [m.get("id") for m in convo.messages]
                if msg_id not in existing_ids:
                    convo.messages.append(message_json)
                    convo.snippet = msg_text
                    convo.updated_time = timezone.now()
                    convo.save()
                    logger.info(f"💾 Saved new message for {sender_name}: {msg_text}")
                else:
                    logger.info(f"⚠️ Duplicate message ignored: {msg_id}")

        return Response({"status": "success"})
