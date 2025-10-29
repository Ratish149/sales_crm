from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .models import PromoCode
from .serializers import (
    PromoCodeDetailSerializer,
    PromoCodeSerializer,
    PromoCodeValidationSerializer,
)

# Create your views here.


class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class PromoCodeListCreateView(generics.ListCreateAPIView):
    queryset = PromoCode.objects.all()
    serializer_class = PromoCodeSerializer
    pagination_class = CustomPagination


class PromoCodeRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PromoCode.objects.all()
    serializer_class = PromoCodeSerializer


@api_view(["POST"])
def validate_promo_code(request):
    """
    Validate a promo code and return discount details if valid

    POST /api/promo-code/validate/
    Body: {"code": "SAVE20"}
    """
    serializer = PromoCodeValidationSerializer(data=request.data)

    if serializer.is_valid():
        code = serializer.validated_data["code"].upper()

        try:
            promo_code = PromoCode.objects.get(code=code)

            # Get validity status and message from model
            is_valid, message = promo_code.is_valid()

            if not is_valid:
                return Response(
                    {"valid": False, "message": message},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Return promo code details
            promo_serializer = PromoCodeDetailSerializer(promo_code)
            return Response(
                {
                    "valid": True,
                    "message": message,
                    "promo_code": promo_serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        except PromoCode.DoesNotExist:
            return Response(
                {"valid": False, "message": "Invalid promo code"},
                status=status.HTTP_404_NOT_FOUND,
            )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
