from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication


class TenantJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication that enforces tenant ownership.

    After validating the JWT token, it checks that the authenticated user
    is the owner of the current tenant (set on request.tenant by
    CustomDomainTenantMiddleware via the X-Tenant-Domain header).

    If the user is NOT the tenant owner → raises PermissionDenied (HTTP 403).

    Edge cases that are allowed through:
    - No token provided → let permission_classes decide (401 / 403)
    - No tenant on request (public schema context) → allow through
    - Tenant has no owner set yet (initial setup edge case) → allow through

    Views using CustomerJWTAuthentication are unaffected because they
    explicitly override authentication_classes.
    """

    def authenticate(self, request):
        result = super().authenticate(request)

        # No token provided — let permission classes handle it
        if result is None:
            return None

        user, validated_token = result
        tenant = getattr(request, "tenant", None)

        # No tenant context (e.g. public schema requests) — allow through
        if tenant is None:
            return result

        # Tenant has no owner set — allow through (edge case: initial setup)
        owner_id = getattr(tenant, "owner_id", None)
        if owner_id is None:
            return result

        # The authenticated user must be the owner of this tenant
        if user.pk != owner_id:
            raise PermissionDenied(
                detail="You do not have permission to access this tenant's data.",
                code="tenant_access_denied",
            )

        return user, validated_token
