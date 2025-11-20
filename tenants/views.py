# Create your views here.
import json  # You already have this, but confirm
import logging
import os

import requests
from django.db import connection
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.utils.text import slugify
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django_filters import rest_framework as django_filters
from dotenv import load_dotenv
from rest_framework import filters, generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from tenants.models import (
    Client,
    Domain,
    FacebookPageTenantMap,
    TemplateCategory,
    TemplateSubCategory,
)

from .serializers import (
    DomainSerializer,
    TemplateCategorySerializer,
    TemplateSubCategorySerializer,
    TemplateTenantSerializer,
)

load_dotenv()
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
BACKEND_DOMAIN = os.getenv("BACKEND_DOMAIN")
HTTP = os.getenv("HTTP")


logger = logging.getLogger("facebook_webhook")


class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class TemplateCategoryListCreateView(generics.ListCreateAPIView):
    queryset = TemplateCategory.objects.all()
    serializer_class = TemplateCategorySerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["name"]


class TemplateCategoryRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TemplateCategory.objects.all()
    serializer_class = TemplateCategorySerializer
    lookup_field = "slug"


# ---------------------------
# TemplateSubCategory Views
# ---------------------------


class SubCategoryFilterSet(django_filters.FilterSet):
    category = django_filters.NumberFilter(
        field_name="category__id", lookup_expr="exact"
    )

    class Meta:
        model = TemplateSubCategory
        fields = ["category"]


class TemplateSubCategoryListCreateView(generics.ListCreateAPIView):
    queryset = TemplateSubCategory.objects.all()
    serializer_class = TemplateSubCategorySerializer
    filter_backends = [django_filters.DjangoFilterBackend, filters.SearchFilter]
    filterset_class = SubCategoryFilterSet
    search_fields = ["name"]


class TemplateSubCategoryRetrieveUpdateDeleteView(
    generics.RetrieveUpdateDestroyAPIView
):
    queryset = TemplateSubCategory.objects.all()
    serializer_class = TemplateSubCategorySerializer
    lookup_field = "slug"


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
            tenant_url = f"{HTTP}://{tenant_schema}.{BACKEND_DOMAIN}/api/facebook/tenant-webhook/"
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


class TemplateTenantFilter(django_filters.FilterSet):
    category = django_filters.CharFilter(
        field_name="template_category__slug", lookup_expr="icontains"
    )
    subcategory = django_filters.CharFilter(
        field_name="template_subcategory__slug", lookup_expr="icontains"
    )

    class Meta:
        model = Client
        fields = ["category", "subcategory"]


class TemplateTenantListAPIView(generics.ListAPIView):
    """
    Get all template tenants with domain info
    """

    serializer_class = TemplateTenantSerializer
    pagination_class = CustomPagination
    filter_backends = [django_filters.DjangoFilterBackend, filters.SearchFilter]
    filterset_class = TemplateTenantFilter
    search_fields = ["name", "owner__owned_stores__store_name"]

    def get_queryset(self):
        return (
            Client.objects.filter(is_template_account=True)
            .select_related("owner")
            .prefetch_related("owner__owned_stores")
            .distinct()
        )


class TemplateTenantRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a template tenant (based on owner_id).
    Drops the corresponding schema on delete.
    """

    queryset = Client.objects.filter(is_template_account=True)
    serializer_class = TemplateTenantSerializer
    lookup_field = "owner_id"  # Important!

    def destroy(self, request, *args, **kwargs):
        # Get the tenant by owner_id instead of pk
        owner_id = self.kwargs.get(self.lookup_field)
        instance = get_object_or_404(
            Client, owner_id=owner_id, is_template_account=True
        )
        schema_name = instance.schema_name

        try:
            # 1️⃣ Drop schema safely
            with connection.cursor() as cursor:
                cursor.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE;')

            # 2️⃣ Delete the tenant object
            instance.delete()

            return Response(
                {
                    "message": f"Template tenant with owner {owner_id} and schema '{schema_name}' deleted successfully."
                },
                status=status.HTTP_204_NO_CONTENT,
            )

        except Exception as e:
            return Response(
                {
                    "error": f"Failed to delete tenant or schema '{schema_name}': {str(e)}"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ClientTokenByIdAPIView(APIView):
    """
    Generate JWT tokens for a client owner using client ID.
    """

    def post(self, request):
        client_id = request.data.get("client_id")
        if not client_id:
            return Response(
                {"detail": "client_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Get the client
        try:
            client = Client.objects.get(id=client_id)
        except Client.DoesNotExist:
            return Response(
                {"detail": "Client not found"}, status=status.HTTP_404_NOT_FOUND
            )

        owner = client.owner
        if not owner:
            return Response(
                {"detail": "Client owner not found"}, status=status.HTTP_404_NOT_FOUND
            )

        domain = Domain.objects.get(tenant=client)
        domain_name = domain.domain
        # Get the first store profile to generate subdomain from store name
        store_profile = owner.owned_stores.first() or owner.stores.first()
        sub_domain = (
            slugify(store_profile.store_name)
            if store_profile and store_profile.store_name
            else domain_name.split(".")[0]
        )

        # Get store profile if it exists
        store_profile = None
        has_profile = False
        store_name = None

        # Check if owner has any associated store profiles
        if hasattr(owner, "owned_stores") and owner.owned_stores.exists():
            store_profile = owner.owned_stores.first()
            has_profile = True
            store_name = store_profile.store_name
        # Also check if user is associated with any stores through the many-to-many relationship
        elif hasattr(owner, "stores") and owner.stores.exists():
            store_profile = owner.stores.first()
            has_profile = True
            store_name = store_profile.store_name

        # Generate JWT tokens
        refresh = RefreshToken.for_user(owner)
        refresh["email"] = owner.email
        refresh["client_id"] = client.id
        refresh["client_name"] = client.name
        refresh["schema_name"] = client.schema_name
        refresh["is_template_account"] = client.is_template_account
        refresh["domain"] = domain_name
        refresh["sub_domain"] = sub_domain

        # Add store related information
        refresh["store_name"] = store_name
        refresh["has_profile"] = has_profile

        response_data = {
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
            "owner": {
                "id": owner.id,
                "email": owner.email,
                "role": owner.role,
                "sub_domain": sub_domain,
                "has_profile": has_profile,
            },
            "client": {
                "id": client.id,
                "name": client.name,
                "schema_name": client.schema_name,
                "is_template_account": client.is_template_account,
                "domain": domain_name,
            },
        }

        # Add store info if profile exists
        if store_name:
            response_data["store"] = {
                "name": store_name,
                "has_profile": has_profile,
                "sub_domain": sub_domain,
            }

        return Response(response_data)
