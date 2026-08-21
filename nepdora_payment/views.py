from decimal import Decimal

from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django_filters import rest_framework as django_filters
from django_filters.rest_framework import DjangoFilterBackend
from django_tenants.utils import schema_context
from rest_framework import filters, generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.utils import log_user_activity
from sales_crm.authentication import TenantJWTAuthentication
from sales_crm.pagination import CustomPagination
from tenants.models import Client

from .models import NepdoraPayment, TenantCentralPaymentHistory, TenantTransferHistory
from .serializers import (
    NepdoraPaymentSerializer,
    TenantCentralPaymentHistorySerializer,
    TenantTransferHistorySerializer,
)

# ─── NepdoraPayment (gateway credentials) ────────────────────────────────────


class NepdoraPaymentListCreateView(generics.ListCreateAPIView):
    queryset = NepdoraPayment.objects.only(
        "id", "payment_type", "secret_key", "merchant_code"
    )
    serializer_class = NepdoraPaymentSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["payment_type"]

    def get_authenticators(self):
        if self.request.method == "POST":
            return [TenantJWTAuthentication()]
        return []

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return super().get_permissions()


class NepdoraPaymentRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = NepdoraPayment.objects.only(
        "id", "payment_type", "secret_key", "merchant_code"
    )
    serializer_class = NepdoraPaymentSerializer
    authentication_classes = [TenantJWTAuthentication]
    permission_classes = [IsAuthenticated]


# ─── Tenant Central Payment History ──────────────────────────────────────────


class TenantCentralPaymentHistoryFilter(django_filters.FilterSet):
    tenant = django_filters.CharFilter(field_name="tenant__name", lookup_expr="exact")

    class Meta:
        model = TenantCentralPaymentHistory
        fields = ["tenant"]


class TenantCentralPaymentHistoryListCreateView(generics.ListCreateAPIView):
    queryset = (
        TenantCentralPaymentHistory.objects
        .select_related("tenant")
        .only(
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
            "tenant__id",
            "tenant__name",  # only tenant fields used in serializer/filter
        )
        .order_by("-created_at")  # consistent ordering avoids unpredictable pagination
    )
    serializer_class = TenantCentralPaymentHistorySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = TenantCentralPaymentHistoryFilter
    search_fields = ["transaction_id", "tenant__name"]
    pagination_class = CustomPagination

    def get_authenticators(self):
        if self.request.method == "POST":
            return [TenantJWTAuthentication()]
        return []

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return super().get_permissions()

    def perform_create(self, serializer):
        instance = serializer.save()
        log_user_activity(
            user=self.request.user,
            action="purchase_subscription",
            description=f"User purchased subscription. Amount: {instance.pay_amount}, Type: {instance.payment_type}",
            metadata={
                "pay_amount": str(instance.pay_amount),
                "payment_type": instance.payment_type,
                "transaction_id": instance.transaction_id,
                "tenant_name": instance.tenant.name,  # already fetched via select_related
            },
        )


class TenantCentralPaymentHistoryRetrieveUpdateDestroyView(
    generics.RetrieveUpdateDestroyAPIView
):
    queryset = TenantCentralPaymentHistory.objects.select_related("tenant").only(
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
        "tenant__id",
        "tenant__name",
    )
    serializer_class = TenantCentralPaymentHistorySerializer
    authentication_classes = [TenantJWTAuthentication]
    permission_classes = [IsAuthenticated]


# ─── Tenant Transfer History ──────────────────────────────────────────────────


class TenantTransferHistoryFilter(django_filters.FilterSet):
    tenant = django_filters.CharFilter(field_name="tenant__name", lookup_expr="exact")
    date_range = django_filters.DateFromToRangeFilter(field_name="transfer_date")

    class Meta:
        model = TenantTransferHistory
        fields = ["tenant", "date_range"]


class TenantTransferHistoryListCreateView(generics.ListCreateAPIView):
    queryset = (
        TenantTransferHistory.objects
        .select_related("tenant")
        .only(
            "id",
            "amount",
            "transfer_date",
            "reference_note",
            "is_read",
            "created_at",
            "updated_at",
            "tenant__id",
            "tenant__name",
        )
        .order_by("-transfer_date")
    )
    serializer_class = TenantTransferHistorySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = TenantTransferHistoryFilter
    search_fields = ["tenant__name"]
    pagination_class = CustomPagination

    def get_authenticators(self):
        if self.request.method == "POST":
            return [TenantJWTAuthentication()]
        return []

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return super().get_permissions()


class TenantTransferHistoryRetrieveUpdateDestroyView(
    generics.RetrieveUpdateDestroyAPIView
):
    queryset = TenantTransferHistory.objects.select_related("tenant").only(
        "id",
        "amount",
        "transfer_date",
        "reference_note",
        "is_read",
        "created_at",
        "updated_at",
        "tenant__id",
        "tenant__name",
    )
    serializer_class = TenantTransferHistorySerializer
    authentication_classes = [TenantJWTAuthentication]
    permission_classes = [IsAuthenticated]


# ─── Payment Summary ──────────────────────────────────────────────────────────


class PaymentSummaryAPIView(APIView):
    """
    Returns aggregated payment totals.

    Optional query param:
      - ?tenant=<tenant_name>  — filter results to a specific tenant
    """

    def get(self, request, *args, **kwargs):
        from django.db.models import Sum

        tenant_name_param = request.query_params.get("tenant")

        # .only() is intentionally skipped here — Sum aggregation
        # does not load model instances, so only() has no effect on aggregates.
        # We defer the import-time queryset and filter inline for clarity.
        received_qs = TenantCentralPaymentHistory.objects.all()
        transferred_qs = TenantTransferHistory.objects.all()

        if tenant_name_param:
            received_qs = received_qs.filter(tenant__name=tenant_name_param)
            transferred_qs = transferred_qs.filter(tenant__name=tenant_name_param)

        total_received = received_qs.aggregate(total=Sum("pay_amount"))[
            "total"
        ] or Decimal("0.00")
        total_paid = transferred_qs.aggregate(total=Sum("amount"))["total"] or Decimal(
            "0.00"
        )
        pending_balance = total_received - total_paid

        return Response(
            {
                "tenant_name": tenant_name_param or "All Tenants",
                "total_received": total_received,
                "total_paid": total_paid,
                "pending_balance": pending_balance,
            },
            status=status.HTTP_200_OK,
        )


# ─── Public NPS Webhook Listener ─────────────────────────────────────────────


@method_decorator(csrf_exempt, name="dispatch")
class PublicNPSWebhookListenerAPIView(APIView):
    """
    Public webhook listener endpoint for NPS payment notifications.
    URL pattern: /api/nps/webhook/<str:schema_name>/
    Receives server-to-server notifications from NPS and updates NPSTransaction & Order inside the tenant database schema.
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request, schema_name, *args, **kwargs):
        return self._process_webhook(request, schema_name)

    def post(self, request, schema_name, *args, **kwargs):
        return self._process_webhook(request, schema_name)

    def _process_webhook(self, request, schema_name):
        merchant_txn_id = (
            request.query_params.get("MerchantTxnId")
            or request.query_params.get("merchant_txn_id")
            or (
                request.data.get("MerchantTxnId")
                if isinstance(request.data, dict)
                else None
            )
            or (
                request.data.get("merchant_txn_id")
                if isinstance(request.data, dict)
                else None
            )
        )
        gateway_txn_id = (
            request.query_params.get("GatewayTxnId")
            or request.query_params.get("gateway_txn_id")
            or (
                request.data.get("GatewayTxnId")
                if isinstance(request.data, dict)
                else None
            )
            or (
                request.data.get("gateway_txn_id")
                if isinstance(request.data, dict)
                else None
            )
        )

        if not merchant_txn_id:
            return HttpResponse("invalid request", status=400)

        # 1. Resolve tenant client by schema_name
        try:
            client = Client.objects.get(schema_name=schema_name)
        except Client.DoesNotExist:
            return HttpResponse("tenant not found", status=404)

        # 2. Process inside tenant schema context
        with schema_context(client.schema_name):
            from nps_payment.models import NPSConfig, NPSTransaction
            from nps_payment.services import verify_transaction_status

            txn = NPSTransaction.objects.filter(merchant_txn_id=merchant_txn_id).first()
            if not txn:
                return HttpResponse("transaction not found", status=404)

            if (
                txn.webhook_received_at is not None
                and str(txn.status).lower() == "success"
            ):
                return HttpResponse("already received", status=200)

            config = NPSConfig.objects.filter(is_enabled=True).first()
            if not config:
                return HttpResponse("config missing", status=500)

            # Server-to-server verification with NPS server
            success, status_res = verify_transaction_status(config, merchant_txn_id)
            txn.webhook_received_at = now()
            if gateway_txn_id:
                txn.gateway_txn_id = gateway_txn_id
            txn.raw_response = status_res

            if success and status_res.get("data"):
                data = status_res["data"]
                txn_status = data.get("Status", "Fail")
                txn.status = txn_status
                txn.institution = data.get("Institution", "")
                txn.instrument = data.get("Instrument", "")
                txn.cbs_message = data.get("CbsMessage", "")
                try:
                    txn.service_charge = float(data.get("ServiceCharge", 0.0))
                except (ValueError, TypeError):
                    pass

                if str(txn_status).strip().lower() in ["success", "0"]:
                    txn.status = "Success"
                    if txn.order:
                        txn.order.is_paid = True
                        txn.order.status = "confirmed"
                        txn.order.transaction_id = merchant_txn_id
                        txn.order.save(
                            update_fields=["is_paid", "status", "transaction_id"]
                        )
            else:
                txn.status = "Fail"

            txn.save()
            return HttpResponse("received", status=200)
