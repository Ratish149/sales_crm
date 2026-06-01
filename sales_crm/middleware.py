import asyncio
from datetime import date
from urllib.parse import urlparse

from asgiref.sync import sync_to_async
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.db import connection
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django_tenants.utils import (
    get_public_schema_name,
    get_tenant_domain_model,
)

from tenants.models import Client

# =====================================================
# CONFIG
# =====================================================

SAFE_METHODS = ("GET", "HEAD", "OPTIONS")

EXEMPT_PATHS = (
    "/admin",
    "/login",
    "/signup",
    "/api/upgrade",
)

WHITELISTED_IPS = {
    "127.0.0.1",
    "::1",
    "172.188.98.151",
}

# =====================================================
# RATE LIMIT MIDDLEWARE
# =====================================================


class RateLimitMiddleware(MiddlewareMixin):
    RATE_LIMIT = 1000
    WINDOW = 60
    BLOCK_TIME = 300

    def process_request(self, request):
        path = request.path.lower()
        if any(path.startswith(p) for p in EXEMPT_PATHS):
            return None

        ip = self.get_client_ip(request)
        if not ip or ip in WHITELISTED_IPS:
            return None

        tenant = getattr(request, "tenant", None)
        tenant_schema = tenant.schema_name if tenant else "public"

        blocked_key = f"blocked:{tenant_schema}:{ip}"
        rate_key = f"ratelimit:{tenant_schema}:{ip}"

        if cache.get(blocked_key):
            return JsonResponse({"detail": "Too Many Requests"}, status=429)

        try:
            cache.add(rate_key, 0, timeout=self.WINDOW)
            count = cache.incr(rate_key)
        except ValueError:
            cache.set(rate_key, 1, timeout=self.WINDOW)
            count = 1
        except Exception:
            return None

        if count > self.RATE_LIMIT:
            cache.set(blocked_key, True, timeout=self.BLOCK_TIME)
            return JsonResponse({"detail": "Too Many Requests"}, status=429)

        return None

    def get_client_ip(self, request):
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")


# =====================================================
# TENANT MIDDLEWARE (FIXED)
# =====================================================


class CustomDomainTenantMiddleware:
    CACHE_TIMEOUT = 300
    TENANT_REQUIRED_PATHS = ("/api/",)
    PUBLIC_API_PATHS = (
        "/api/schema/",
        "/api/docs/",
        "/api/redoc/",
        "/api/support/",
        "/api/stores/",
    )

    def __init__(self, get_response):
        self.get_response = get_response
        if asyncio.iscoroutinefunction(self.get_response):
            self._is_coroutine = asyncio.coroutines._is_coroutine

    def __call__(self, request):
        if asyncio.iscoroutinefunction(self.get_response):
            return self.__acall__(request)
        return self._sync_call(request)

    # --------------------------------------------------
    # ASYNC
    # --------------------------------------------------

    async def __acall__(self, request):
        await sync_to_async(connection.set_schema_to_public)()

        path = request.path.lower()

        if path.startswith(("/static", "/media")):
            await sync_to_async(self.set_public_tenant)(request)
            return await self.get_response(request)

        try:
            tenant = await sync_to_async(self.resolve_tenant)(request)
            await sync_to_async(connection.set_tenant)(tenant)
            request.tenant = tenant
        except (ObjectDoesNotExist, Client.DoesNotExist):
            await sync_to_async(self.set_public_tenant)(request)

            if self.requires_tenant(path):
                return JsonResponse(
                    {
                        "detail": "Tenant could not be resolved",
                        "hint": "Send X-Tenant-Domain header",
                    },
                    status=400,
                )

        try:
            return await self.get_response(request)
        finally:
            await sync_to_async(connection.set_schema_to_public)()

    # --------------------------------------------------
    # SYNC
    # --------------------------------------------------

    def _sync_call(self, request):
        connection.set_schema_to_public()

        path = request.path.lower()

        if path.startswith(("/static", "/media")):
            self.set_public_tenant(request)
            return self.get_response(request)

        try:
            tenant = self.resolve_tenant(request)
            connection.set_tenant(tenant)
            request.tenant = tenant
        except (ObjectDoesNotExist, Client.DoesNotExist):
            self.set_public_tenant(request)

            if self.requires_tenant(path):
                return JsonResponse(
                    {"detail": "Tenant could not be resolved"},
                    status=400,
                )

        try:
            return self.get_response(request)
        finally:
            connection.set_schema_to_public()

    # --------------------------------------------------
    # CORE FIX: SAFE HOST RESOLUTION
    # --------------------------------------------------

    def resolve_tenant(self, request):
        DomainModel = get_tenant_domain_model()

        for hostname in self.tenant_host_candidates(request):
            hostname = self.normalize_hostname(hostname)
            if not hostname:
                continue

            cache_key = f"tenant_domain:{hostname}"
            tenant_id = cache.get(cache_key)

            try:
                if tenant_id is None:
                    domain_obj = (
                        DomainModel.objects
                        .select_related("tenant")
                        .only("tenant__id")
                        .get(domain=hostname)
                    )
                    tenant_id = domain_obj.tenant_id
                    cache.set(cache_key, tenant_id, timeout=self.CACHE_TIMEOUT)

                return Client.objects.get(id=tenant_id)

            except (ObjectDoesNotExist, Client.DoesNotExist):
                cache.delete(cache_key)
                continue

        raise Client.DoesNotExist

    # --------------------------------------------------
    # FIXED: ONLY STABLE SOURCES
    # --------------------------------------------------

    def tenant_host_candidates(self, request):
        return [
            request.headers.get("X-Tenant-Domain"),
            request.headers.get("Host"),
            request.get_host(),
        ]

    # --------------------------------------------------
    # 🔥 IMPORTANT FIX: hostname normalization
    # --------------------------------------------------

    def normalize_hostname(self, value):
        if not value:
            return None

        value = value.strip().lower()

        if "://" in value:
            parsed = urlparse(value)
            hostname = parsed.hostname
        else:
            hostname = value.split("/")[0].split(":")[0]

        if not hostname:
            return None

        # FIX: unify www and non-www
        hostname = hostname.replace("www.", "").strip()

        return hostname

    def set_public_tenant(self, request):
        connection.set_schema_to_public()
        try:
            request.tenant = Client.objects.get(schema_name=get_public_schema_name())
        except Client.DoesNotExist:
            request.tenant = None

    def requires_tenant(self, path):
        if not path.startswith(self.TENANT_REQUIRED_PATHS):
            return False
        return not path.startswith(self.PUBLIC_API_PATHS)


# =====================================================
# SUBSCRIPTION MIDDLEWARE (UNCHANGED LOGIC)
# =====================================================


class SubscriptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        if asyncio.iscoroutinefunction(self.get_response):
            self._is_coroutine = asyncio.coroutines._is_coroutine

    def __call__(self, request):
        if asyncio.iscoroutinefunction(self.get_response):
            return self.__acall__(request)
        return self._sync_call(request)

    async def __acall__(self, request):
        blocked = await sync_to_async(self._check_subscription)(request)
        if blocked:
            return blocked
        return await self.get_response(request)

    def _sync_call(self, request):
        blocked = self._check_subscription(request)
        if blocked:
            return blocked
        return self.get_response(request)

    def _check_subscription(self, request):
        path = request.path.lower()

        if any(p in path for p in EXEMPT_PATHS):
            return None

        tenant = getattr(request, "tenant", None)
        if not tenant or tenant.schema_name == get_public_schema_name():
            return None

        is_active = self.is_subscription_active(tenant)
        request.tenant_is_active = is_active

        if not is_active and request.method not in SAFE_METHODS:
            return JsonResponse(
                {
                    "detail": "Subscription expired",
                    "plan": tenant.pricing_plan.name if tenant.pricing_plan else None,
                    "paid_until": tenant.paid_until,
                },
                status=403,
            )

        return None

    def is_subscription_active(self, tenant):
        cache_key = f"tenant_sub:{tenant.schema_name}"
        cached = cache.get(cache_key)

        if cached is not None:
            return cached

        if not tenant.pricing_plan_id:
            active = False
        elif tenant.paid_until is None:
            active = True
        else:
            active = tenant.paid_until >= date.today()

        cache.set(cache_key, active, timeout=300)
        return active


# =====================================================
# CSRF EXEMPT
# =====================================================


class CSRFExemptForAllauthHeadless:
    def __init__(self, get_response):
        self.get_response = get_response
        if asyncio.iscoroutinefunction(self.get_response):
            self._is_coroutine = asyncio.coroutines._is_coroutine

    def __call__(self, request):
        if asyncio.iscoroutinefunction(self.get_response):
            return self.__acall__(request)
        return self._sync_call(request)

    async def __acall__(self, request):
        if request.path.startswith("/_allauth/browser/v1/"):
            setattr(request, "_dont_enforce_csrf_checks", True)
        return await self.get_response(request)

    def _sync_call(self, request):
        if request.path.startswith("/_allauth/browser/v1/"):
            setattr(request, "_dont_enforce_csrf_checks", True)
        return self.get_response(request)
