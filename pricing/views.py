# Create your views here.
# pricing/views.py
from datetime import date, timedelta

from rest_framework import generics, permissions, status
from rest_framework.response import Response

from sales_crm.utils.decorators import allow_inactive_subscription
from tenants.models import Client

from .models import Pricing
from .serializers import PricingSerializer


class PricingListView(generics.ListAPIView):
    queryset = Pricing.objects.all().order_by("price")
    serializer_class = PricingSerializer
    permission_classes = [permissions.AllowAny]


@allow_inactive_subscription
class TenantUpgradePlanView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        plan_id = request.data.get("plan_id")
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
        duration_days = plan.get_duration_days()  # uses duration_days or fallback
        if duration_days is None:
            # Lifetime plan
            tenant.paid_until = None
        else:
            if tenant.paid_until and tenant.paid_until > date.today():
                tenant.paid_until += timedelta(days=duration_days)
            else:
                tenant.paid_until = date.today() + timedelta(days=duration_days)

        tenant.save()

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
