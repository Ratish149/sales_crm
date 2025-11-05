import json  # You already have this, but confirm

from django.db import connection, transaction
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics, response, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from tenants.models import FacebookPageTenantMap

from .models import Conversation, Facebook
from .serializers import (
    ConversationMessageSerializer,
    ConversationSerializer,
    FacebookSerializer,
)
from .utils import sync_conversations_from_facebook, sync_messages_for_conversation

VERIFY_TOKEN = "YOUR_OWN_SECRET_FACEBOOK_VERIFY_TOKEN"


class FacebookListCreateView(generics.ListCreateAPIView):
    queryset = Facebook.objects.all()
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


@api_view(["POST"])
def webhook_handler(request):
    """
    Webhook to receive real-time message data from frontend.

    Expected format from your frontend:
    {
        "id": "m_xxx",
        "conversationId": "t_122170001792604595" or "t_775429945664166_32735928529331376",
        "message": "Hello",
        "from": {
            "id": "32735928529331376",
            "name": "Facebook User"
        },
        "created_time": "2025-11-03T08:24:15.000Z",
        "pageId": "775429945664166",
        "senderId": "32735928529331376"
    }
    """
    try:
        # Extract data from frontend format
        message_id = request.data.get("id")
        conversation_id = request.data.get("conversationId")
        message_text = request.data.get("message", "")
        sender_info = request.data.get("from", {})
        created_time_str = request.data.get("created_time")
        page_id = request.data.get("pageId")
        sender_id = request.data.get("senderId")

        # Validate required fields
        if not all([message_id, conversation_id, page_id, sender_id]):
            return Response(
                {
                    "error": "Missing required fields: id, conversationId, pageId, senderId"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get Facebook page
        try:
            page = Facebook.objects.get(page_id=page_id, is_enabled=True)
        except Facebook.DoesNotExist:
            return Response(
                {"error": f"Facebook page {page_id} not found or disabled"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Parse created_time
        if created_time_str:
            try:
                created_time = parse_datetime(created_time_str)
                if not created_time:
                    created_time = timezone.now()
            except:
                created_time = timezone.now()
        else:
            created_time = timezone.now()

        # Try to find existing conversation by conversation_id
        try:
            conversation = Conversation.objects.get(
                conversation_id=conversation_id, page=page
            )
            created = False
        except Conversation.DoesNotExist:
            # Create new conversation
            conversation = Conversation.objects.create(
                conversation_id=conversation_id,
                page=page,
                participants=[],
                snippet=message_text,
                updated_time=created_time,
                messages=[],
                last_synced=timezone.now(),
            )
            created = True

        # Check if message already exists
        existing_message_ids = {msg.get("id") for msg in conversation.messages}

        message_status = "no_change"
        if message_id and message_id not in existing_message_ids:
            # Create message in your database format
            new_message = {
                "id": message_id,
                "from": {
                    "id": sender_id,
                    "name": sender_info.get("name", "Facebook User"),
                    "email": f"{sender_id}@facebook.com",
                },
                "message": message_text,
                "created_time": created_time.strftime("%Y-%m-%dT%H:%M:%S+0000"),
            }

            # Append message
            conversation.messages.append(new_message)

            # Sort messages by created_time
            conversation.messages.sort(key=lambda x: x.get("created_time", ""))

            # Update snippet with latest message
            conversation.snippet = message_text

            # Update updated_time
            conversation.updated_time = created_time

            message_status = "added"
        elif message_id in existing_message_ids:
            message_status = "duplicate"

        # Update participants if sender is new
        participant_ids = {p.get("id") for p in conversation.participants}
        if sender_id and sender_id not in participant_ids:
            conversation.participants.append(
                {"id": sender_id, "name": sender_info.get("name", "Facebook User")}
            )

        # Also add page as participant if not exists
        page_id_str = str(page_id)
        if page_id_str not in participant_ids:
            conversation.participants.append(
                {"id": page_id_str, "name": page.page_name or "Page"}
            )

        # Update last_synced
        conversation.last_synced = timezone.now()
        conversation.save()

        return Response(
            {
                "status": "success",
                "conversation_created": created,
                "message_status": message_status,
                "total_messages": len(conversation.messages),
                "conversation": {
                    "id": conversation.id,
                    "conversation_id": conversation.conversation_id,
                    "page_name": page.page_name,
                    "snippet": conversation.snippet,
                    "updated_time": conversation.updated_time.isoformat()
                    if conversation.updated_time
                    else None,
                    "participants": conversation.participants,
                },
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        import traceback

        return Response(
            {"error": str(e), "traceback": traceback.format_exc()},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@method_decorator(csrf_exempt, name="dispatch")
class FacebookWebhookView(View):
    """
    Handles the raw Facebook Webhook GET (verification) and POST (message events).
    Includes logic for switching tenants based on the Page ID using FacebookPageTenantMap.
    """

    # --- GET: Verification Challenge ---
    def get(self, request, *args, **kwargs):
        """Handle Facebook's GET request for verification."""
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")

        if mode and token:
            if mode == "subscribe" and token == VERIFY_TOKEN:
                # Respond with the challenge token to complete verification
                return HttpResponse(challenge, status=200)
            else:
                return HttpResponseForbidden("Verification token mismatch")

        return HttpResponseBadRequest("Missing verification parameters")

    # --- POST: Incoming Messages with Tenant Switching ---
    def post(self, request, *args, **kwargs):
        """Handles the POST request containing message payloads."""
        try:
            # Facebook sends raw JSON body
            data = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            # Respond quickly
            return HttpResponseBadRequest("Invalid JSON payload")

        if data.get("object") != "page":
            return HttpResponseForbidden("Not a page object")

        for entry in data.get("entry", []):
            page_fb_id = entry.get("id")

            # --- 🔑 CORE TENANT IDENTIFICATION AND SWITCHING ---
            try:
                # 1. Ensure the connection is set to the public schema for the lookup
                connection.set_schema_to_public()

                # 2. Query the Public Schema Map using the Facebook Page ID
                page_map = FacebookPageTenantMap.objects.select_related("tenant").get(
                    page_id=page_fb_id
                )

                # 3. Switch the database connection to the identified tenant's schema
                tenant = page_map.tenant
                connection.set_tenant(tenant)

            except FacebookPageTenantMap.DoesNotExist:
                # If no mapping exists, skip this entry and clean up
                connection.set_schema_to_public()
                continue

            # --- Processing in the Correct Tenant Context ---
            with transaction.atomic():
                try:
                    # Retrieve the tenant's Facebook object (now safe to do in tenant schema)
                    facebook_page = Facebook.objects.get(
                        page_id=page_fb_id, is_enabled=True
                    )
                except Facebook.DoesNotExist:
                    continue  # Page not configured/enabled in this tenant

                for event in entry.get("messaging", []):
                    if "message" in event:
                        self._handle_message(facebook_page, event)

            # 4. Clean up: reset connection back to public for safety/next entry
            connection.set_schema_to_public()

        # Respond quickly with 200 OK (Facebook requirement)
        return HttpResponse("EVENT_RECEIVED", status=200)

    # --- Message Processing Utility (Adapted from your original logic) ---
    def _handle_message(self, facebook_page, event):
        """Processes the incoming Facebook message event and saves it."""

        sender_id = event["sender"]["id"]
        recipient_id = event["recipient"]["id"]
        timestamp = event["timestamp"]
        message_data = event["message"]

        message_id = message_data.get("mid")
        message_text = message_data.get("text", "")

        # Use Page ID + Sender ID (user PSID) as a unique conversation key
        conversation_id = f"{facebook_page.page_id}-{sender_id}"

        # Convert timestamp (ms) to datetime object
        created_datetime = timezone.datetime.fromtimestamp(
            timestamp / 1000.0, tz=timezone.utc
        )

        # Structure the message object to match your JSONField format
        message_obj = {
            "id": message_id,
            "from": {
                "id": sender_id,
                "name": "Facebook User",
            },  # Name might need a graph API lookup
            "message": message_text,
            "created_time": created_datetime.isoformat(),
        }

        # 1. Get or Create the Conversation
        conversation, created = Conversation.objects.get_or_create(
            page=facebook_page,
            conversation_id=conversation_id,
            defaults={
                "participants": [
                    {"id": sender_id, "name": "Facebook User"},
                    {"id": recipient_id, "name": facebook_page.page_name or "Page"},
                ],
                "snippet": message_text[:255] or "New message",
                "updated_time": created_datetime,
                "messages": [message_obj],
                "last_synced": timezone.now(),
            },
        )

        # 2. Append/Update Conversation if not created
        if not created:
            existing_message_ids = {msg.get("id") for msg in conversation.messages}

            if message_id and message_id not in existing_message_ids:
                # Append message
                conversation.messages.append(message_obj)

                # Sort messages by created_time (optional, but good practice)
                conversation.messages.sort(key=lambda x: x.get("created_time", ""))

                # Update conversation metadata
                conversation.snippet = message_text
                conversation.updated_time = created_datetime
                conversation.last_synced = timezone.now()
                conversation.save()

            elif message_id in existing_message_ids:
                # Message already processed, just update last synced time
                conversation.updated_time = created_datetime
                conversation.last_synced = timezone.now()
                conversation.save()


# Remove or comment out the old webhook_handler:
# @api_view(["POST"])
# def webhook_handler(request):
#     ...
#     (This is replaced by the FacebookWebhookView class)
