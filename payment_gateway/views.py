from django_filters import rest_framework as django_filters
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from sales_crm.authentication import TenantJWTAuthentication
from sales_crm.pagination import CustomPagination

from .models import Payment, PaymentHistory, PaymentQR
from .serializers import (
    PaymentHistorySerializer,
    PaymentQRSerializer,
    PaymentSerializer,
    PaymentSmallSerializer,
)

# reusable querysets
PAYMENT_QS = Payment.objects.only(
    "id", "payment_type", "secret_key", "merchant_code", "is_enabled"
)
PAYMENT_SMALL_QS = Payment.objects.only("id", "payment_type", "is_enabled")
PAYMENT_HISTORY_QS = PaymentHistory.objects.only(
    "id",
    "payment_type",
    "pay_amount",
    "transaction_id",
    "products_purchased",
    "status",
    "additional_info",
    "is_read",
    "created_at",
    "updated_at",
)


class PaymentFilterSet(django_filters.FilterSet):
    payment_type = django_filters.CharFilter(
        field_name="payment_type", lookup_expr="iexact"
    )

    class Meta:
        model = Payment
        fields = ["payment_type"]


class PaymentListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = PaymentSerializer
    filter_backends = [django_filters.DjangoFilterBackend]
    filterset_class = PaymentFilterSet

    def get_authenticators(self):
        if self.request.method == "POST":
            return [TenantJWTAuthentication()]
        return []

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        # GET uses PaymentSmallSerializer which only needs 3 fields
        if self.request.method == "GET":
            return PAYMENT_SMALL_QS
        return PAYMENT_QS

    def get_serializer_class(self):
        if self.request.method == "GET":
            return PaymentSmallSerializer
        return PaymentSerializer

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        if response.status_code == 201:
            instance_data = response.data
            response.data = {
                "id": instance_data.get("id"),
                "payment_type": instance_data.get("payment_type"),
                "merchant_code": instance_data.get("merchant_code"),
            }
        return response


class PaymentRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PAYMENT_QS
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [TenantJWTAuthentication]

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        if response.status_code == 200:
            instance_data = response.data
            response.data = {
                "id": instance_data.get("id"),
                "payment_type": instance_data.get("payment_type"),
                "merchant_code": instance_data.get("merchant_code"),
            }
        return response


class PaymentListAPIView(generics.ListAPIView):
    queryset = PAYMENT_QS
    serializer_class = PaymentSerializer


class PaymentHistoryListCreateAPIView(generics.ListCreateAPIView):
    queryset = PAYMENT_HISTORY_QS
    serializer_class = PaymentHistorySerializer
    pagination_class = CustomPagination

    def get_authenticators(self):
        if self.request.method == "GET":
            return [TenantJWTAuthentication()]
        return []

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return super().get_permissions()


class PaymentHistoryRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PAYMENT_HISTORY_QS
    serializer_class = PaymentHistorySerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [TenantJWTAuthentication]


class PaymentQRFilterSet(django_filters.FilterSet):
    payment_type = django_filters.CharFilter(
        field_name="payment_type", lookup_expr="iexact"
    )

    class Meta:
        model = PaymentQR
        fields = ["payment_type"]


class PaymentQRListCreateAPIView(generics.ListCreateAPIView):
    queryset = PaymentQR.objects.all()
    serializer_class = PaymentQRSerializer
    filter_backends = [django_filters.DjangoFilterBackend]
    filterset_class = PaymentQRFilterSet

    def get_authenticators(self):
        if self.request.method == "POST":
            return [TenantJWTAuthentication()]
        return []

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return super().get_permissions()


class PaymentQRRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PaymentQR.objects.all()
    serializer_class = PaymentQRSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [TenantJWTAuthentication]
