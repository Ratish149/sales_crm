# Create your views here.
import json  # You already have this, but confirm
import logging
import os

import requests
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from dotenv import load_dotenv
from rest_framework import generics
from rest_framework.pagination import PageNumberPagination

from tenants.models import FacebookPageTenantMap

from .models import Domain
from .serializers import DomainSerializer

load_dotenv()
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
BACKEND_DOMAIN = os.getenv("BACKEND_DOMAIN")

logger = logging.getLogger("facebook_webhook")


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
class FacebookWebhookView(View):
    """Webhook endpoint that receives messages from Facebook and routes to correct tenant backend."""

    def get(self, request, *args, **kwargs):
        """Verify Facebook webhook"""
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")

        print(f"GET webhook hit: mode={mode}, token={token}, challenge={challenge}")
        logger.info(
            f"GET webhook hit: mode={mode}, token={token}, challenge={challenge}"
        )

        if mode == "subscribe" and token == VERIFY_TOKEN:
            print("✅ Facebook webhook verified.")
            logger.info("✅ Facebook webhook verified.")
            return HttpResponse(challenge)
        else:
            print("❌ Invalid verification token.")
            logger.warning("❌ Invalid verification token.")
            return HttpResponseForbidden("Invalid token")

    def post(self, request, *args, **kwargs):
        """Receive webhook event and route to tenant"""
        print("📩 POST webhook hit!")
        logger.info("📩 POST webhook hit!")

        try:
            payload = json.loads(request.body)
            print("Payload received:", json.dumps(payload, indent=2))
            logger.debug(f"📦 Payload:\n{json.dumps(payload, indent=2)}")
        except json.JSONDecodeError:
            print("❌ Invalid JSON received")
            logger.error("❌ Invalid JSON received")
            return HttpResponseBadRequest("Invalid JSON")

        if payload.get("object") != "page":
            print("⚠️ Not a page object.")
            logger.warning("⚠️ Not a page object.")
            return HttpResponseForbidden("Not a page event")

        for entry in payload.get("entry", []):
            page_id = entry.get("id")
            print(f"➡️ Processing entry for page_id: {page_id}")
            logger.info(f"➡️ Processing entry for page_id: {page_id}")

            if not page_id:
                print("⚠️ Missing page_id in entry.")
                logger.warning("⚠️ Missing page_id in entry.")
                continue

            # Step 1: find tenant mapping
            try:
                mapping = FacebookPageTenantMap.objects.get(page_id=page_id)
                tenant = mapping.tenant
                tenant_schema = tenant.schema_name
                print(f"✅ Found tenant: {tenant_schema} for page_id {page_id}")
                logger.info(f"✅ Found tenant: {tenant_schema} for page_id {page_id}")
            except FacebookPageTenantMap.DoesNotExist:
                print(f"❌ No tenant mapping found for page_id: {page_id}")
                logger.warning(f"❌ No tenant mapping found for page_id: {page_id}")
                continue
            except Exception as e:
                print(f"🚨 Error fetching tenant mapping: {e}")
                logger.error(f"🚨 Error fetching tenant mapping: {e}")
                continue

            # Step 2: forward to tenant API
            tenant_url = (
                f"https://{tenant_schema}.{BACKEND_DOMAIN}/api/facebook/tenant-webhook/"
            )
            print(f"🌐 Forwarding to {tenant_url}")
            logger.info(f"🌐 Forwarding to {tenant_url}")

            try:
                resp = requests.post(
                    tenant_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=10,
                )
                print(
                    f"✅ Forwarded successfully to {tenant_schema}: {resp.status_code} → {resp.text}"
                )
                logger.info(
                    f"➡️ Forwarded to {tenant_schema} ({resp.status_code}): {resp.text}"
                )
            except Exception as e:
                print(f"🚨 Failed forwarding to {tenant_schema}: {e}")
                logger.error(f"🚨 Failed forwarding to {tenant_schema}: {e}")

        print("🏁 Webhook processing finished.")
        logger.info("🏁 Webhook processing finished.")
        return HttpResponse("EVENT_RECEIVED", status=200)
