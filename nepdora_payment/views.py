from decimal import Decimal

from django_filters import rest_framework as django_filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from sales_crm.pagination import CustomPagination

from .models import NepdoraPayment, TenantCentralPaymentHistory, TenantTransferHistory
from .serializers import (
    NepdoraPaymentSerializer,
    TenantCentralPaymentHistorySerializer,
    TenantTransferHistorySerializer,
)

# ─── NepdoraPayment (gateway credentials) ────────────────────────────────────


class NepdoraPaymentListCreateView(generics.ListCreateAPIView):
    queryset = NepdoraPayment.objects.all()
    serializer_class = NepdoraPaymentSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["payment_type"]


class NepdoraPaymentRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = NepdoraPayment.objects.all()
    serializer_class = NepdoraPaymentSerializer


# ─── Tenant Central Payment History ──────────────────────────────────────────


class TenantCentralPaymentHistoryFilter(django_filters.FilterSet):
    tenant = django_filters.CharFilter(field_name="tenant__name", lookup_expr="exact")

    class Meta:
        model = TenantCentralPaymentHistory
        fields = ["tenant"]


class TenantCentralPaymentHistoryListCreateView(generics.ListCreateAPIView):
    queryset = TenantCentralPaymentHistory.objects.all().select_related("tenant")
    serializer_class = TenantCentralPaymentHistorySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = TenantCentralPaymentHistoryFilter
    search_fields = ["transaction_id"]
    pagination_class = CustomPagination


class TenantCentralPaymentHistoryRetrieveUpdateDestroyView(
    generics.RetrieveUpdateDestroyAPIView
):
    queryset = TenantCentralPaymentHistory.objects.all()
    serializer_class = TenantCentralPaymentHistorySerializer


# ─── Tenant Transfer History ──────────────────────────────────────────────────


class TenantTransferHistoryListCreateView(generics.ListCreateAPIView):
    queryset = TenantTransferHistory.objects.all().select_related("tenant")
    serializer_class = TenantTransferHistorySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["tenant"]
    pagination_class = CustomPagination


class TenantTransferHistoryRetrieveUpdateDestroyView(
    generics.RetrieveUpdateDestroyAPIView
):
    queryset = TenantTransferHistory.objects.all()
    serializer_class = TenantTransferHistorySerializer


# ─── Payment Summary ──────────────────────────────────────────────────────────


class PaymentSummaryAPIView(APIView):
    """
    Returns aggregated payment totals.

    Optional query param:
      - ?tenant=<tenant_id>  — filter results to a specific tenant
    """

    def get(self, request, *args, **kwargs):
        from django.db.models import Sum

        tenant_id = request.query_params.get("tenant")

        received_qs = TenantCentralPaymentHistory.objects.all()
        transferred_qs = TenantTransferHistory.objects.all()

        if tenant_id:
            received_qs = received_qs.filter(tenant_id=tenant_id)
            transferred_qs = transferred_qs.filter(tenant_id=tenant_id)

        total_received = received_qs.aggregate(total=Sum("pay_amount"))[
            "total"
        ] or Decimal("0.00")
        total_paid = transferred_qs.aggregate(total=Sum("amount"))["total"] or Decimal(
            "0.00"
        )
        pending_balance = total_received - total_paid

        return Response(
            {
                "total_received": total_received,
                "total_paid": total_paid,
                "pending_balance": pending_balance,
            },
            status=status.HTTP_200_OK,
        )
