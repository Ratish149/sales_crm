from rest_framework import generics

from .models import OurPricing
from .serializers import OurPricingSerializer


class OurPricingListCreateAPIView(generics.ListCreateAPIView):
    """
    API view to list all pricing plans and create new ones.
    GET: Returns all pricing plans with their features
    POST: Creates a new pricing plan with features
    """

    queryset = OurPricing.objects.all()
    serializer_class = OurPricingSerializer

    def get_queryset(self):
        """Optimize query by prefetching related features"""
        return OurPricing.objects.prefetch_related("features").all()


class OurPricingRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    API view to retrieve, update, or delete a specific pricing plan.
    GET: Returns a single pricing plan with its features
    PUT/PATCH: Updates a pricing plan and its features
    DELETE: Deletes a pricing plan (features are cascade deleted)
    """

    queryset = OurPricing.objects.all()
    serializer_class = OurPricingSerializer
    lookup_field = "pk"

    def get_queryset(self):
        """Optimize query by prefetching related features"""
        return OurPricing.objects.prefetch_related("features").all()
