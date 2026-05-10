from django.db.models import Prefetch
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from sales_crm.authentication import TenantJWTAuthentication

from .models import OurPricing, OurPricingFeature
from .serializers import OurPricingSerializer

# single reusable queryset — avoids defining get_queryset() twice
PRICING_OPTIMIZED_QS = OurPricing.objects.prefetch_related(
    Prefetch(
        "features",
        queryset=OurPricingFeature.objects.only(
            "id", "pricing_id", "feature", "order", "created_at", "updated_at"
        ).order_by("order"),  # matches model Meta ordering, explicit is safer
    )
).only("id", "name", "price", "description", "is_popular", "created_at", "updated_at")


class OurPricingListCreateAPIView(generics.ListCreateAPIView):
    queryset = PRICING_OPTIMIZED_QS
    serializer_class = OurPricingSerializer

    def get_authenticators(self):
        if self.request.method == "POST":
            return [TenantJWTAuthentication()]
        return []

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return super().get_permissions()


class OurPricingRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PRICING_OPTIMIZED_QS
    serializer_class = OurPricingSerializer
    lookup_field = "pk"
    permission_classes = [IsAuthenticated]
    authentication_classes = [TenantJWTAuthentication]
