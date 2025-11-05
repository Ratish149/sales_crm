# Create your views here.
import json  # You already have this, but confirm
from datetime import datetime
from datetime import timezone as dt_timezone

from django.db import connection, transaction
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django_tenants.utils import get_tenant_model, schema_context
from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from facebook.models import Conversation, Facebook
from tenants.models import FacebookPageTenantMap

from .models import Domain
from .serializers import DomainSerializer

VERIFY_TOKEN = "secret123"


class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class DomainView(generics.ListCreateAPIView):
    queryset = Domain.objects.all()
    serializer_class = DomainSerializer
    pagination_class = CustomPagination


class DomainDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Domain.objects.all()
    serializer_class = DomainSerializer


@method_decorator(csrf_exempt, name="dispatch")
class FacebookWebhookAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")
        print("GET webhook hit:", mode, token, challenge)

        if mode and token:
            if mode == "subscribe" and token == VERIFY_TOKEN:
                print("GET verification successful")
                return HttpResponse(challenge, status=200)
            else:
                print("GET verification failed: token mismatch")
                return HttpResponseForbidden("Verification token mismatch")
        return HttpResponseBadRequest("Missing verification parameters")

    def post(self, request, *args, **kwargs):
        print("POST webhook hit!")
        try:
            data = json.loads(request.body.decode("utf-8"))
            print("Payload received:", json.dumps(data, indent=2))
        except json.JSONDecodeError:
            print("Invalid JSON received")
            return HttpResponseBadRequest("Invalid JSON payload")

        if data.get("object") != "page":
            print("Not a page object")
            return HttpResponseForbidden("Not a page object")

        for entry in data.get("entry", []):
            page_fb_id = entry.get("id")
            print("Processing entry for Page ID:", page_fb_id)

            tenant = self.find_tenant_by_page_id(page_fb_id)
            if not tenant:
                print("No tenant has this page ID")
                continue

            print("Tenant found:", tenant.schema_name)

            try:
                connection.set_tenant(tenant)
                print(f"Switched to tenant: {tenant.schema_name}")
            except Exception as e:
                print("Error switching tenant:", e)
                continue

            try:
                facebook_page = Facebook.objects.get(
                    page_id=page_fb_id, is_enabled=True
                )
                print("Facebook page found in tenant:", facebook_page.page_name)
            except Facebook.DoesNotExist:
                print("Facebook page not enabled in tenant")
                connection.set_schema_to_public()
                continue
            except Exception as e:
                print("Error fetching Facebook page:", e)
                connection.set_schema_to_public()
                continue

            try:
                with transaction.atomic():
                    for event in entry.get("messaging", []):
                        if "message" in event:
                            print("Processing message event:", event)
                            self._handle_message(facebook_page, event)
            except Exception as e:
                print("Error processing messages:", e)
            finally:
                connection.set_schema_to_public()

        print("Webhook processing finished")
        return HttpResponse("EVENT_RECEIVED", status=200)

    def find_tenant_by_page_id(self, page_id):
        TenantModel = get_tenant_model()
        for tenant in TenantModel.objects.all():
            try:
                with schema_context(tenant.schema_name):
                    if FacebookPageTenantMap.objects.filter(page_id=page_id).exists():
                        return tenant
            except Exception as e:
                print("Error checking tenant schema:", tenant.schema_name, e)
        return None

    def _handle_message(self, facebook_page, event):
        try:
            sender_id = event["sender"]["id"]
            recipient_id = event["recipient"]["id"]
            timestamp = event["timestamp"]
            message_data = event["message"]

            message_id = message_data.get("mid")
            message_text = message_data.get("text", "")

            print(f"Handling message {message_id} from {sender_id}: {message_text}")

            conversation_id = f"{facebook_page.page_id}-{sender_id}"
            created_datetime = datetime.fromtimestamp(
                timestamp / 1000.0, tz=dt_timezone.utc
            )

            message_obj = {
                "id": message_id,
                "from": {"id": sender_id, "name": "Facebook User"},
                "message": message_text,
                "created_time": created_datetime.isoformat(),
            }

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

            if not created:
                existing_ids = {m.get("id") for m in conversation.messages}
                if message_id not in existing_ids:
                    conversation.messages.append(message_obj)
                    conversation.messages.sort(key=lambda x: x["created_time"])
                    conversation.snippet = message_text
                    conversation.updated_time = created_datetime
                    conversation.last_synced = timezone.now()
                    conversation.save()
                else:
                    conversation.updated_time = created_datetime
                    conversation.last_synced = timezone.now()
                    conversation.save()

            print(f"Conversation {conversation.conversation_id} processed")
        except Exception as e:
            print("Error in _handle_message:", e)
