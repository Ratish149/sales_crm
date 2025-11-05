# Create your views here.
# pricing/views.py
from datetime import date, timedelta

from rest_framework import generics, permissions, status
from rest_framework.response import Response

from sales_crm.utils.decorators import allow_inactive_subscription
from tenants.models import Client

from .models import Pricing, UserSubscription
from .serializers import PricingSerializer, UserSubscriptionSerializer


class PricingListView(generics.ListAPIView):
    queryset = Pricing.objects.all().order_by("price")
    serializer_class = PricingSerializer
    permission_classes = [permissions.AllowAny]


@allow_inactive_subscription
class TenantUpgradePlanView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        plan_id = request.data.get("plan_id")
        transaction_id = request.data.get("transaction_id")
        payment_type = request.data.get("payment_type", "cash")  # default to cash

        if not plan_id:
            return Response({"error": "plan_id is required"}, status=400)

        try:
            plan = Pricing.objects.get(id=plan_id)
        except Pricing.DoesNotExist:
            return Response({"error": "Invalid plan_id"}, status=400)

        try:
            tenant = Client.objects.get(owner=request.user)
        except Client.DoesNotExist:
            return Response({"error": "Tenant not found for this user"}, status=400)

        # Assign the plan
        tenant.pricing_plan = plan

        # Extend subscription based on plan's duration_days
        duration_days = plan.get_duration_days()
        if duration_days is None:
            # Lifetime plan
            tenant.paid_until = None
        else:
            if tenant.paid_until and tenant.paid_until > date.today():
                tenant.paid_until += timedelta(days=duration_days)
            else:
                tenant.paid_until = date.today() + timedelta(days=duration_days)

        tenant.save()

        # Create subscription history record
        UserSubscription.objects.create(
            tenant=tenant,
            plan=plan,
            transaction_id=transaction_id,
            payment_type=payment_type,
            amount=plan.price,
            started_on=date.today(),
            expires_on=tenant.paid_until,
        )

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
            },
            status=status.HTTP_200_OK,
        )


class UserSubscriptionListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSubscriptionSerializer

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

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            tenant = Client.objects.get(owner=request.user)
        except Client.DoesNotExist:
            return Response({"error": "Tenant not found for this user"}, status=404)

        if tenant.pricing_plan is None:
            # No plan => inactive
            status_flag = False
            status_text = "inactive"
        elif tenant.paid_until is None:
            # Lifetime plan => active
            status_flag = True
            status_text = "active"
        else:
            # Check expiry date
            if tenant.paid_until >= date.today():
                status_flag = True
                status_text = "active"
            else:
                status_flag = False
                status_text = "inactive"

        return Response(
            {
                "active": status_flag,
                "status": status_text,
                "plan": tenant.pricing_plan.name if tenant.pricing_plan else "No plan",
                "expires_on": tenant.paid_until if tenant.paid_until else "Never",
            }
        )