# Create your views here.
# import json  # You already have this, but confirm
import logging
import os

from django.core.exceptions import ValidationError

# import requests
from django.db import connection, transaction
from django.db.utils import IntegrityError

# from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404

# from django.utils.decorators import method_decorator
from django.utils.text import slugify

# from django.views import View
# from django.views.decorators.csrf import csrf_exempt
from django_filters import rest_framework as django_filters
from django_tenants.utils import schema_context
from dotenv import load_dotenv
from rest_framework import filters, generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import CustomUser
from payment_gateway.models import Payment
from tenants.models import (
    Client,
    Domain,
    # FacebookPageTenantMap,
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


class DomainFilter(django_filters.FilterSet):
    payment = django_filters.CharFilter(method="filter_payment")

    class Meta:
        model = Domain
        fields = ["payment"]

    def filter_payment(self, queryset, name, value):
        if not value:
            return queryset

        enabled_tenant_ids = []
        # Get all clients except public
        clients = Client.objects.exclude(schema_name="public")

        for client in clients:
            with schema_context(client.schema_name):
                # Check if any payment gateway is enabled for this tenant
                if Payment.objects.filter(is_enabled=True).exists():
                    enabled_tenant_ids.append(client.id)

        if value.lower() == "enabled":
            return queryset.filter(tenant_id__in=enabled_tenant_ids)
        elif value.lower() == "disabled":
            return queryset.exclude(tenant_id__in=enabled_tenant_ids)

        return queryset


class DomainView(generics.ListCreateAPIView):
    queryset = Domain.objects.all().order_by("-id")
    serializer_class = DomainSerializer
    pagination_class = CustomPagination
    filter_backends = [django_filters.DjangoFilterBackend, filters.SearchFilter]
    filterset_class = DomainFilter
    search_fields = [
        "domain",
        "tenant__name",
        "tenant__owner__email",
        "tenant__owner__username",
    ]


class DomainDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Domain.objects.all()
    serializer_class = DomainSerializer


# @method_decorator(csrf_exempt, name="dispatch")
# class FacebookWebhookView(View):
#     """Webhook endpoint that receives messages from Facebook and routes to correct tenant backend."""

#     def get(self, request, *args, **kwargs):
#         """Verify Facebook webhook"""
#         mode = request.GET.get("hub.mode")
#         token = request.GET.get("hub.verify_token")
#         challenge = request.GET.get("hub.challenge")

#         print(f"GET webhook hit: mode={mode}, token={token}, challenge={challenge}")
#         logger.info(
#             f"GET webhook hit: mode={mode}, token={token}, challenge={challenge}"
#         )

#         if mode == "subscribe" and token == VERIFY_TOKEN:
#             print("✅ Facebook webhook verified.")
#             logger.info("✅ Facebook webhook verified.")
#             return HttpResponse(challenge)
#         else:
#             print("❌ Invalid verification token.")
#             logger.warning("❌ Invalid verification token.")
#             return HttpResponseForbidden("Invalid token")

#     def post(self, request, *args, **kwargs):
#         """Receive webhook event and route to tenant"""
#         print("📩 POST webhook hit!")
#         logger.info("📩 POST webhook hit!")

#         try:
#             payload = json.loads(request.body)
#             print("Payload received:", json.dumps(payload, indent=2))
#             logger.debug(f"📦 Payload:\n{json.dumps(payload, indent=2)}")
#         except json.JSONDecodeError:
#             print("❌ Invalid JSON received")
#             logger.error("❌ Invalid JSON received")
#             return HttpResponseBadRequest("Invalid JSON")

#         if payload.get("object") != "page":
#             print("⚠️ Not a page object.")
#             logger.warning("⚠️ Not a page object.")
#             return HttpResponseForbidden("Not a page event")

#         for entry in payload.get("entry", []):
#             page_id = entry.get("id")
#             print(f"➡️ Processing entry for page_id: {page_id}")
#             logger.info(f"➡️ Processing entry for page_id: {page_id}")

#             if not page_id:
#                 print("⚠️ Missing page_id in entry.")
#                 logger.warning("⚠️ Missing page_id in entry.")
#                 continue

#             # Step 1: find tenant mapping
#             try:
#                 mapping = FacebookPageTenantMap.objects.get(page_id=page_id)
#                 tenant = mapping.tenant
#                 tenant_schema = tenant.schema_name
#                 print(f"✅ Found tenant: {tenant_schema} for page_id {page_id}")
#                 logger.info(f"✅ Found tenant: {tenant_schema} for page_id {page_id}")
#             except FacebookPageTenantMap.DoesNotExist:
#                 print(f"❌ No tenant mapping found for page_id: {page_id}")
#                 logger.warning(f"❌ No tenant mapping found for page_id: {page_id}")
#                 continue
#             except Exception as e:
#                 print(f"🚨 Error fetching tenant mapping: {e}")
#                 logger.error(f"🚨 Error fetching tenant mapping: {e}")
#                 continue

#             # Step 2: forward to tenant API
#             tenant_url = f"{HTTP}://{tenant_schema}.{BACKEND_DOMAIN}/api/facebook/tenant-webhook/"
#             print(f"🌐 Forwarding to {tenant_url}")
#             logger.info(f"🌐 Forwarding to {tenant_url}")

#             try:
#                 resp = requests.post(
#                     tenant_url,
#                     json=payload,
#                     headers={"Content-Type": "application/json"},
#                     timeout=10,
#                 )
#                 print(
#                     f"✅ Forwarded successfully to {tenant_schema}: {resp.status_code} → {resp.text}"
#                 )
#                 logger.info(
#                     f"➡️ Forwarded to {tenant_schema} ({resp.status_code}): {resp.text}"
#                 )
#             except Exception as e:
#                 print(f"🚨 Failed forwarding to {tenant_schema}: {e}")
#                 logger.error(f"🚨 Failed forwarding to {tenant_schema}: {e}")

#         print("🏁 Webhook processing finished.")
#         logger.info("🏁 Webhook processing finished.")
#         return HttpResponse("EVENT_RECEIVED", status=200)


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
            Client.objects
            .filter(is_template_account=True)
            .select_related("owner")
            .prefetch_related("owner__owned_stores")
            .distinct()
        )


class TemplateTenantRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a template tenant (based on owner_id).
    Deletes the owner user inside tenant schema first, then drops the schema,
    then deletes the tenant object.
    """

    queryset = Client.objects.filter(is_template_account=True)
    serializer_class = TemplateTenantSerializer
    lookup_field = "owner_id"  # Important!

    def destroy(self, request, *args, **kwargs):
        owner_id = self.kwargs.get(self.lookup_field)
        tenant = get_object_or_404(Client, owner_id=owner_id, is_template_account=True)
        schema_name = tenant.schema_name
        user = CustomUser.objects.get(id=owner_id)

        try:
            with transaction.atomic():
                # 1️⃣ Delete the user inside tenant schema first
                with schema_context(schema_name):
                    user.delete()

                # 2️⃣ Drop the tenant schema
                with connection.cursor() as cursor:
                    cursor.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE;')

                # 3️⃣ Delete the tenant object (Client) from public schema
                tenant.delete()

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
        client = Client.objects.filter(id=client_id).first()
        if not client:
            return Response(
                {"detail": "Client not found"}, status=status.HTTP_404_NOT_FOUND
            )

        owner = client.owner
        if not owner:
            return Response(
                {"detail": "Client owner not found"}, status=status.HTTP_404_NOT_FOUND
            )

        domain = Domain.objects.filter(tenant=client).first()
        if not domain:
            return Response(
                {"detail": "Domain not found for this client"},
                status=status.HTTP_404_NOT_FOUND,
            )
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
        refresh["role"] = owner.role
        refresh["client_id"] = client.id
        refresh["client_name"] = client.name
        refresh["schema_name"] = client.schema_name
        refresh["is_template_account"] = client.is_template_account
        refresh["domain"] = domain_name
        refresh["sub_domain"] = sub_domain
        refresh["website_type"] = owner.website_type
        refresh["is_onboarding_complete"] = owner.is_onboarding_complete

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


class TenantInternalRepoView(APIView):
    """
    Internal API to fetch repo_url for a tenant by schema_name.
    """

    def get(self, request, schema_name):
        try:
            client = Client.objects.get(schema_name=schema_name)
            return Response({"repo_url": client.repo_url})
        except Client.DoesNotExist:
            return Response(
                {"error": "Tenant not found"}, status=status.HTTP_404_NOT_FOUND
            )


class TenantDomainView(generics.ListCreateAPIView):
    serializer_class = DomainSerializer

    def get_queryset(self):
        """
        GET: Returns domains scoped strictly to the current tenant context.
        """
        tenant = getattr(self.request, "tenant", None)
        if not tenant:
            return Domain.objects.none()

        queryset = Domain.objects.filter(tenant=tenant).order_by("-id")

        # Filter by specific domain string if passed in query params
        # Usage: /api/domains/?domain_name=mysite.com
        domain_name = self.request.query_params.get("domain_name")
        if domain_name:
            # Clean input to match DB format
            clean_name = domain_name.strip().lower()
            queryset = queryset.filter(domain=clean_name)

        return queryset

    def perform_create(self, serializer):
        """
        POST: Adds a new domain and automatically sets it as the Primary domain.
        """
        current_tenant = getattr(self.request, "tenant", None)

        if not current_tenant:
            raise ValidationError({
                "error": "No tenant context found. Please provide a valid X-Tenant-Domain header."
            })

        # Standardize domain name (remove http://, https://, and trailing slashes)
        raw_domain = self.request.data.get("domain", "").lower()
        clean_domain = (
            raw_domain
            .replace("https://", "")
            .replace("http://", "")
            .split("/")[0]
            .strip()
        )

        # Wrap in an atomic transaction to ensure data consistency
        with transaction.atomic():
            try:
                # 1. Demote all existing domains for this tenant to non-primary
                Domain.objects.filter(tenant=current_tenant).update(is_primary=False)

                # 2. Save the new domain as the NEW Primary
                serializer.save(
                    tenant=current_tenant, domain=clean_domain, is_primary=True
                )
            except IntegrityError:
                raise ValidationError({
                    "domain": "This domain is already registered in the system (possibly by another tenant)."
                })

    def list(self, request, *args, **kwargs):
        """
        Custom list to handle 404s when searching for a specific domain name.
        """
        response = super().list(request, *args, **kwargs)

        # If user searched for a specific domain but it's not in their list
        if not response.data and request.query_params.get("domain_name"):
            return Response(
                {"detail": "Domain not found for this tenant account."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return response
