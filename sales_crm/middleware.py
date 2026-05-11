from datetime import date

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
    RATE_LIMIT = 200
    WINDOW = 60
    BLOCK_TIME = 3600

    def process_request(self, request):
        ip = self.get_client_ip(request)

        if not ip:
            return None

        if ip in WHITELISTED_IPS:
            return None

        blocked_key = f"blocked:{ip}"

        if cache.get(blocked_key):
            return JsonResponse(
                {"detail": "Too Many Requests"},
                status=429,
            )

        rate_key = f"ratelimit:{ip}"

        try:
            cache.add(rate_key, 0, timeout=self.WINDOW)
            count = cache.incr(rate_key)
        except ValueError:
            cache.set(rate_key, 1, timeout=self.WINDOW)
            count = 1
        except Exception:
            # Never break request if Redis fails
            return None

        if count > self.RATE_LIMIT:
            cache.set(
                blocked_key,
                True,
                timeout=self.BLOCK_TIME,
            )

            return JsonResponse(
                {"detail": "Too Many Requests"},
                status=429,
            )

        return None

    def get_client_ip(self, request):
        xff = request.META.get("HTTP_X_FORWARDED_FOR")

        if xff:
            return xff.split(",")[0].strip()

        return request.META.get("REMOTE_ADDR")


# =====================================================
# TENANT MIDDLEWARE
# =====================================================


class CustomDomainTenantMiddleware:
    CACHE_TIMEOUT = 300

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Always reset to public schema FIRST — before any DB query.
        # If this connection was recycled from a previous tenant request,
        # any query (including the domain lookup below) would otherwise
        # run against the wrong tenant schema.
        connection.set_schema_to_public()

        path = request.path.lower()

        # Skip static/admin/media
        if path.startswith(("/admin", "/static", "/media")):
            self.set_public_tenant(request)
            return self.get_response(request)

        hostname = request.headers.get("X-Tenant-Domain") or request.get_host()

        if not hostname:
            self.set_public_tenant(request)
            return self.get_response(request)

        hostname = hostname.split(":")[0].replace("www.", "").strip().lower()

        cache_key = f"tenant_domain:{hostname}"

        try:
            tenant_id = cache.get(cache_key)

            if tenant_id is None:
                DomainModel = get_tenant_domain_model()

                # Safe: connection is guaranteed public schema at this point
                domain_obj = (
                    DomainModel.objects
                    .select_related("tenant")
                    .only("tenant__id")
                    .get(domain=hostname)
                )

                tenant_id = domain_obj.tenant_id

                cache.set(
                    cache_key,
                    tenant_id,
                    timeout=self.CACHE_TIMEOUT,
                )

            tenant = Client.objects.get(id=tenant_id)

            # Switch to tenant schema for the actual request
            connection.set_tenant(tenant)
            request.tenant = tenant

        except (
            ObjectDoesNotExist,
            Client.DoesNotExist,
        ):
            self.set_public_tenant(request)

        response = self.get_response(request)

        # Reset back to public after the response so the connection returns
        # to the pool in a clean state — prevents the next request from
        # inheriting this tenant schema.
        connection.set_schema_to_public()

        return response

    def set_public_tenant(self, request):
        connection.set_schema_to_public()

        try:
            request.tenant = Client.objects.get(schema_name=get_public_schema_name())
        except Client.DoesNotExist:
            request.tenant = None


# =====================================================
# SUBSCRIPTION MIDDLEWARE
# =====================================================


class SubscriptionMiddleware(MiddlewareMixin):
    def process_view(
        self,
        request,
        view_func,
        view_args,
        view_kwargs,
    ):
        path = request.path.lower()

        if any(p in path for p in EXEMPT_PATHS):
            return None

        tenant = getattr(request, "tenant", None)

        if not tenant:
            return None

        if tenant.schema_name == get_public_schema_name():
            return None

        if getattr(
            view_func,
            "allow_inactive_subscription",
            False,
        ):
            return None

        view_class = getattr(view_func, "cls", None)

        if view_class and getattr(
            view_class,
            "allow_inactive_subscription",
            False,
        ):
            return None

        is_active = self.is_subscription_active(tenant)

        request.tenant_is_active = is_active

        if not is_active and request.method not in SAFE_METHODS:
            return JsonResponse(
                {
                    "detail": ("Subscription expired. Read-only mode."),
                    "plan": (
                        tenant.pricing_plan.name if tenant.pricing_plan else "No plan"
                    ),
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

        cache.set(
            cache_key,
            active,
            timeout=300,
        )

        return active


# =====================================================
# CSRF EXEMPT
# =====================================================


class CSRFExemptForAllauthHeadless:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/_allauth/browser/v1/"):
            setattr(
                request,
                "_dont_enforce_csrf_checks",
                True,
            )

        return self.get_response(request)
