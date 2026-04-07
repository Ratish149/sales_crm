from datetime import date

from rest_framework import generics, permissions, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from sales_crm.utils.decorators import allow_inactive_subscription
from tenants.models import Client

from .models import Pricing, UserSubscription
from .serializers import (
    PricingSerializer,
    UserSubscriptionListSerializer,
    UserSubscriptionSerializer,
)


class PricingListView(generics.ListAPIView):
    queryset = Pricing.objects.all().order_by("price")
    serializer_class = PricingSerializer
    permission_classes = [permissions.AllowAny]


@allow_inactive_subscription
class TenantUpgradePlanView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSubscriptionSerializer

    def post(self, request, *args, **kwargs):
        plan_id = request.data.get("plan_id")
        transaction_id = request.data.get("transaction_id")
        payment_type = request.data.get("payment_type", "cash")

        if not plan_id:
            return Response({"error": "plan_id is required"}, status=400)

        try:
            plan = Pricing.objects.get(id=plan_id)
        except Pricing.DoesNotExist:
            return Response({"error": "Invalid plan_id"}, status=400)

        tenant = getattr(request, "tenant", None)
        if not tenant or tenant.schema_name == "public":
            return Response(
                {"error": "Tenant context required for upgrade"}, status=400
            )

        # Assign the plan and extend subscription
        tenant.pricing_plan = plan
        tenant.extend_subscription(plan)

        # Create subscription history record using serializer
        serializer = self.get_serializer(
            data={
                "plan_id": plan.id,
                "transaction_id": transaction_id,
                "payment_type": payment_type,
                "amount": plan.price,
                "started_on": date.today(),
                "expires_on": tenant.paid_until,
            }
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(tenant=tenant, user=request.user)

        return Response(
            {
                "message": f"Successfully upgraded to {plan.name}",
                "unit": plan.unit,
                "plan": {
                    "name": plan.name,
                    "price": str(plan.price),
                    "unit": plan.unit,
                    "expires_on": tenant.paid_until if tenant.paid_until else "Never",
                },
                "subscription": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class UserSubscriptionListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSubscriptionListSerializer

    def get_queryset(self):
        try:
            tenant = Client.objects.get(owner=self.request.user)
        except Client.DoesNotExist:
            return UserSubscription.objects.none()
        return UserSubscription.objects.filter(tenant=tenant)


@allow_inactive_subscription
class SubscriptionStatusView(generics.GenericAPIView):
    """
    Check the current tenant's subscription status.
    Returns `active` or `inactive`.
    """

    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        tenant = getattr(request, "tenant", None)
        if not tenant or tenant.schema_name == "public":
            return Response({"error": "Tenant context required"}, status=400)

        is_active = tenant.is_plan_active()
        status_text = "active" if is_active else "inactive"

        return Response({
            "active": is_active,
            "status": status_text,
            "plan": tenant.pricing_plan.name if tenant.pricing_plan else "No plan",
            "expires_on": tenant.paid_until if tenant.paid_until else "Never",
        })
