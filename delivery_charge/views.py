import os

from django.conf import settings
from django.db.models import Q
from rest_framework import filters, generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DeliveryCharge
from .serializers import DeliveryChargeSerializer
from .utils import import_default_locations


class CustomPagination(PageNumberPagination):
    page_size = 30
    page_size_query_param = "page_size"
    max_page_size = 100


class DeliveryChargeListCreateView(generics.ListCreateAPIView):
    queryset = DeliveryCharge.objects.filter(
        location_name__isnull=False, is_default=False
    ).order_by("location_name")
    serializer_class = DeliveryChargeSerializer
    pagination_class = CustomPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ["location_name"]


class DefaultDeliveryChargeListCreateView(generics.ListCreateAPIView):
    queryset = DeliveryCharge.objects.filter(
        is_default=True, location_name__isnull=True
    )
    serializer_class = DeliveryChargeSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        # Separate default and location-specific charges
        default_prices = queryset.filter(
            (Q(location_name__isnull=True) | Q(location_name="")) & Q(is_default=True)
        )
        # Serialize them separately
        default_serializer = self.get_serializer(default_prices, many=True)

        # Custom response structure
        return Response(
            {
                "default_price": default_serializer.data,
            }
        )


class DeliveryChargeRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = DeliveryCharge.objects.all()
    serializer_class = DeliveryChargeSerializer


class LoadDefaultLocationsAPIView(APIView):
    """Trigger import of default delivery locations from Excel."""

    def post(self, request, *args, **kwargs):
        file_path = os.path.join(
            settings.BASE_DIR, "delivery_charge", "default_locations.xlsx"
        )

        success = import_default_locations(file_path)
        if success:
            return Response(
                {"message": "✅ Default delivery locations imported successfully."},
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"error": "❌ Failed to import default delivery locations."},
            status=status.HTTP_400_BAD_REQUEST,
        )
