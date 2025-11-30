from datetime import date

from django.core.cache import cache
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

SAFE_METHODS = ("GET", "HEAD", "OPTIONS")


EXEMPT_PATHS = [
    "/admin",
    "/login",
    "/signup",
    "/api/upgrade",
]

RATE_LIMIT = (
    3000  # requests per minute (50 req/sec) - suitable for active website building
)

RATE_LIMIT_BLOCK_SECONDS = (
    3600  # 1 hour block (allows recovery from accidental triggers)
)


class RateLimitMiddleware(MiddlewareMixin):
    """
    Rate limit requests based on IP address.
    """

    def process_request(self, request):
        ip = self.get_client_ip(request)
        if not ip:
            return None

        # Check if IP is blocked
        if cache.get(f"blocked:{ip}"):
            return JsonResponse(
                {"detail": "Too Many Requests - IP Blocked"},
                status=429,
            )

        # Increment request count
        key = f"ratelimit:{ip}"
        cache.get_or_set(key, 0, timeout=60)
        count = cache.incr(key)

        if count > RATE_LIMIT:
            cache.set(f"blocked:{ip}", True, timeout=RATE_LIMIT_BLOCK_SECONDS)
            return JsonResponse(
                {"detail": "Too Many Requests - IP Blocked"},
                status=429,
            )

        return None

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip


class CSRFExemptForAllauthHeadless:
    """
    Exempt all requests to allauth headless from CSRF
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/_allauth/browser/v1/"):
            setattr(request, "_dont_enforce_csrf_checks", True)
        response = self.get_response(request)
        return response


class SubscriptionMiddleware(MiddlewareMixin):
    """
    Enforce subscription validity for tenant-based access.
    - Blocks write requests for expired tenants.
    - Allows SAFE_METHODS (GET, HEAD, OPTIONS) even if subscription expired.
    - Attaches request.tenant_is_active flag.
    - Skips explicitly exempted routes and views.
    """

    def process_view(self, request, view_func, view_args, view_kwargs):
        path = request.path.lower()

        # Skip exempt paths
        if any(keyword in path for keyword in EXEMPT_PATHS):
            return None

        tenant = getattr(request, "tenant", None)
        if not tenant:
            # Not tenant scoped (public schema, etc.)
            return None

        # Skip explicitly exempt views
        if getattr(view_func, "allow_inactive_subscription", False):
            return None

        # DRF CBVs sometimes wrap view_func; check cls
        view_class = getattr(view_func, "cls", None)
        if view_class and getattr(view_class, "allow_inactive_subscription", False):
            return None

        # Check subscription status
        is_active = self.check_subscription_active(tenant)
        request.tenant_is_active = is_active

        # If subscription inactive AND method is not safe, block access
        if not is_active and request.method not in SAFE_METHODS:
            return JsonResponse(
                {
                    "detail": "Your subscription has expired. You can view data but cannot create, update, or delete.",
                    "status": "subscription_inactive",
                    "plan": tenant.pricing_plan.name
                    if tenant.pricing_plan
                    else "No plan",
                    "paid_until": tenant.paid_until,
                },
                status=403,
            )

        # If subscription inactive but method is safe, allow view
        return None

    def check_subscription_active(self, tenant):
        """
        Determine if tenant's subscription is active.
        Lifetime plans or paid_until in future are considered active.
        """
        if not tenant.pricing_plan:
            return False  # No plan => inactive

        if tenant.paid_until is None:
            return True  # Lifetime plan => active

        return tenant.paid_until >= date.today()
