import json
import logging
import os
from datetime import datetime

import requests
from django.utils import timezone
from django_tenants.utils import get_public_schema_name, schema_context
from dotenv import load_dotenv
from rest_framework import generics, response
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

load_dotenv()


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
        serializer = self.serializer_class(conversation, context={"request": request})
        return response.Response(
            {
                "conversation": serializer.data,
                "total_messages": len(
                    conversation.messages
                ),  # for frontend to know remaining messages
            },
            status=200,
        )


NEXTJS_FRONTEND_URL = os.getenv("NEXTJS_FRONTEND_URL")  # or your domain


class TenantFacebookWebhookMessageView(APIView):
    """
    Runs inside each tenant.
    Receives forwarded webhook payloads and stores messages (with attachments) in Conversation.
    """

    def post(self, request, *args, **kwargs):
        payload = request.data
        print("Payload received in backend api:", json.dumps(payload, indent=2))
        tenant_schema = (
            getattr(request, "tenant", None).schema_name
            if getattr(request, "tenant", None)
            else "public"
        )
        logger.info(f"📨 Tenant {tenant_schema} webhook received")

        for entry in payload.get("entry", []):
            page_id = entry.get("id")
            messaging_events = entry.get("messaging", [])

            if not page_id or not messaging_events:
                continue

            # Step 1️⃣: Find Facebook Page
            try:
                page = Facebook.objects.get(page_id=page_id)
            except Facebook.DoesNotExist:
                logger.warning(f"⚠️ No Facebook page found for page_id={page_id}")
                continue

            # Step 2️⃣: Process each messaging event
            for event in messaging_events:
                message = event.get("message")
                sender_info = event.get("sender", {})
                recipient_info = event.get("recipient", {})

                if not message:
                    continue

                sender_id = sender_info.get("id")
                recipient_id = recipient_info.get("id")

                if not sender_id or not recipient_id:
                    logger.warning("⚠️ Missing sender or recipient ID.")
                    continue

                msg_text = message.get("text", "")
                msg_id = message.get("mid", "")
                timestamp = event.get("timestamp", None)
                attachments = message.get("attachments", [])

                # Step 3️⃣: Try to find existing conversation
                convo = None
                for c in Conversation.objects.all():
                    participant_ids = [p.get("id") for p in c.participants]
                    if sender_id in participant_ids and recipient_id in participant_ids:
                        convo = c
                        break

                # Step 4️⃣: If not found, fetch from Facebook Graph API
                if not convo:
                    conv_id, sender_name = self.fetch_conversation_from_facebook(
                        page, sender_id, recipient_id
                    )
                    logger.info(
                        f"📞 Fetched conversation from Facebook for sender {sender_id}: {conv_id}"
                    )
                    profile_pic = None
                    try:
                        user_resp = requests.get(
                            f"https://graph.facebook.com/{sender_id}",
                            params={
                                "fields": "name,picture.type(large)",
                                "access_token": page.page_access_token,
                            },
                            timeout=5,
                        ).json()
                        profile_pic = (
                            user_resp.get("picture", {}).get("data", {}).get("url")
                        )
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to fetch profile picture: {e}")

                    convo, _ = Conversation.objects.get_or_create(
                        conversation_id=conv_id,
                        page=page,
                        defaults={
                            "participants": [
                                {
                                    "id": sender_id,
                                    "name": sender_name,
                                    "profile_pic": profile_pic,
                                },
                                {
                                    "id": page.page_id,
                                    "name": getattr(page, "page_name", "Page"),
                                    "profile_pic": None,
                                },
                            ],
                            "messages": [],
                        },
                    )
                else:
                    conv_id = convo.conversation_id
                    sender_name = next(
                        (p["name"] for p in convo.participants if p["id"] == sender_id),
                        sender_id,
                    )
                    logger.info(f"✅ Existing conversation for sender {sender_id}")

                # Step 5️⃣: Build message JSON
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
                    "attachments": [],
                }

                # Step 6️⃣: Handle attachments
                for att in attachments:
                    att_type = att.get("type")
                    att_payload = att.get("payload", {})
                    message_json["attachments"].append(
                        {
                            "type": att_type,
                            "url": att_payload.get("url"),
                            "sticker_id": att_payload.get("sticker_id"),
                        }
                    )

                # Step 7️⃣: Avoid duplicate messages
                existing_ids = [m.get("id") for m in convo.messages]
                if msg_id not in existing_ids:
                    convo.messages.append(message_json)
                    convo.snippet = msg_text or (
                        f"[{len(attachments)} attachment(s)]" if attachments else ""
                    )
                    convo.updated_time = timezone.now()
                    convo.save()
                    logger.info(
                        f"💾 Saved new message for {sender_name}: {msg_text or 'Attachment'}"
                    )

                    # Step 8️⃣: Notify frontend
                    self.notify_frontend(
                        tenant_schema=tenant_schema,
                        conversation_id=conv_id,
                        message=message_json,
                        page_id=page_id,
                        snippet=convo.snippet,
                        sender_name=sender_name,
                        sender_id=sender_id,
                    )
                else:
                    logger.info(f"⚠️ Duplicate message ignored: {msg_id}")

        return Response({"status": "success"})

    # -------------------------------------------------------------------
    # 📞 Fetch Facebook Conversation ID
    # -------------------------------------------------------------------
    def fetch_conversation_from_facebook(self, page, sender_id, recipient_id):
        """
        Fetch the official Facebook conversation ID and sender name.
        """
        fallback_conv_id = f"{sender_id}-{recipient_id}"
        sender_name = sender_id

        try:
            url = f"https://graph.facebook.com/v20.0/{page.page_id}/conversations"
            params = {
                "access_token": page.page_access_token,
                "fields": "participants,id",
                "limit": 50,
            }

            while url:
                response = requests.get(url, params=params)
                data = response.json()

                if response.status_code != 200:
                    logger.warning(f"⚠️ Graph API error: {data}")
                    break

                for conv in data.get("data", []):
                    participants = conv.get("participants", {}).get("data", [])
                    participant_ids = [p["id"] for p in participants]

                    # Check if sender_id is part of this conversation
                    if sender_id in participant_ids:
                        conv_id = conv["id"]
                        for p in participants:
                            if p["id"] == sender_id:
                                sender_name = p.get("name", sender_id)
                        return conv_id, sender_name

                # Move to next page if available
                url = data.get("paging", {}).get("next")
                params = {}

        except Exception as e:
            logger.warning(
                f"⚠️ Failed to fetch official conversation from Facebook: {e}"
            )

        return fallback_conv_id, sender_name

    # -------------------------------------------------------------------
    # 🔔 Notify Frontend
    # -------------------------------------------------------------------
    def notify_frontend(
        self,
        tenant_schema,
        conversation_id,
        message,
        page_id,
        snippet,
        sender_name,
        sender_id,
    ):
        """Send POST request to Next.js API route."""
        try:
            notification_url = f"{NEXTJS_FRONTEND_URL}/api/webhook/"
            print("Notification URL:", notification_url)

            payload = {
                "tenant": tenant_schema,
                "type": "new_message",
                "data": {
                    "conversation_id": conversation_id,
                    "message": message,
                    "page_id": page_id,
                    "snippet": snippet,
                    "sender_name": sender_name,
                    "sender_id": sender_id,
                    "timestamp": message.get("created_time"),
                    "message_type": "attachment"
                    if message.get("attachments")
                    else "text",
                },
            }

            print("Payload to frontend:", json.dumps(payload, indent=2))
            logger.info(f"🚀 Sending frontend notification to {notification_url}")

            response = requests.post(
                notification_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=5,
            )

            if response.status_code == 200:
                logger.info(
                    f"✅ Frontend notified successfully for tenant {tenant_schema}"
                )
            else:
                logger.warning(
                    f"⚠️ Frontend notification failed ({response.status_code}): {response.text}"
                )

        except Exception as e:
            logger.error(f"❌ Error notifying frontend: {e}")
