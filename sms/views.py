from django_tenants.utils import schema_context
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from nepdora_payment.models import SMSPurchaseHistory
from order.models import Order
from sales_crm.authentication import TenantJWTAuthentication
from sales_crm.pagination import CustomPagination
from sms.serializers import SMSPurchaseListSerializer
from tenants.models import Client

from .models import SMSSendHistory, SMSSetting
from .serializers import (
    SendCustomSMSSerializer,
    SMSPurchaseHistorySerializer,
    SMSSendHistorySerializer,
    SMSSettingSerializer,
    TenantSMSSettingSerializer,
)
from .utils import add_sms_credits, send_sms_test


class SMSSettingListCreateView(generics.ListCreateAPIView):
    serializer_class = SMSSettingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SMSSetting.objects.all()

    def perform_create(self, serializer):
        # ensure only one setting exists
        if SMSSetting.objects.exists():
            return
        serializer.save()


class SMSSettingDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SMSSettingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SMSSetting.objects.all()

    def get_object(self):
        obj = SMSSetting.load()
        return obj


class SMSPurchaseListCreateView(generics.ListCreateAPIView):
    """
    List and record SMS credit purchases.
    """

    serializer_class = SMSPurchaseHistorySerializer
    pagination_class = CustomPagination

    def get_authenticators(self):
        if self.request.method == "POST":
            return [TenantJWTAuthentication()]
        return []

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        return SMSPurchaseHistory.objects.filter(tenant=self.request.tenant).order_by(
            "-purchased_at"
        )

    def perform_create(self, serializer):
        # Use utility to ensure SMS credit is updated in the same transaction
        add_sms_credits(
            tenant=self.request.tenant,
            amount=serializer.validated_data["amount"],
            payment_type=serializer.validated_data["payment_type"],
            transaction_id=serializer.validated_data["transaction_id"],
            price=serializer.validated_data.get("price"),
        )


class AdminSMSListCreateView(generics.ListCreateAPIView):
    def get_serializer_class(self):
        if self.request.method == "GET":
            return SMSPurchaseListSerializer
        return SMSPurchaseHistorySerializer

    def get_queryset(self):
        queryset = SMSPurchaseHistory.objects.all().order_by("-purchased_at")
        client_id = self.request.query_params.get("client")
        if client_id:
            queryset = queryset.filter(tenant__id=client_id)
        return queryset

    def perform_create(self, serializer):
        client_id = serializer.validated_data.get("client")
        if not client_id:
            raise ValidationError({"client": "This field is required."})
        tenant = Client.objects.get(id=client_id)
        # Use utility to ensure SMS credit is updated in the same transaction
        add_sms_credits(
            tenant=tenant,
            amount=serializer.validated_data["amount"],
            payment_type=serializer.validated_data["payment_type"],
            transaction_id=serializer.validated_data["transaction_id"],
            price=serializer.validated_data.get("price"),
        )


class SMSPurchaseDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a specific purchase record.
    """

    serializer_class = SMSPurchaseHistorySerializer

    def get_authenticators(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [TenantJWTAuthentication()]
        return []

    def get_permissions(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        return SMSPurchaseHistory.objects.filter(tenant=self.request.tenant)


class SMSSendHistoryListCreateView(generics.ListCreateAPIView):
    """
    List SMS history or Send a new SMS (via POST).
    """

    serializer_class = SMSSendHistorySerializer
    pagination_class = CustomPagination

    def get_authenticators(self):
        if self.request.method == "POST":
            return [TenantJWTAuthentication()]
        return []

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        return SMSSendHistory.objects.all().order_by("-sent_at")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Extract data from either model fields or aliases
        to = serializer.validated_data.get(
            "receiver_number"
        ) or serializer.validated_data.get("to")
        text = serializer.validated_data.get(
            "message"
        ) or serializer.validated_data.get("text")

        if not to or not text:
            return Response(
                {
                    "error": "Both receiver_number (or 'to') and message (or 'text') are required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = send_sms_test(to=to, text=text)

        if result["success"]:
            # The utility already created the history record.
            history = SMSSendHistory.objects.latest("sent_at")
            response_serializer = self.get_serializer(history)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        return Response(result, status=status.HTTP_400_BAD_REQUEST)


class SMSSendHistoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a specific SMS history record.
    """

    serializer_class = SMSSendHistorySerializer

    def get_authenticators(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [TenantJWTAuthentication()]
        return []

    def get_permissions(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        return SMSSendHistory.objects.all()


class SMSBalanceView(APIView):
    """
    Get current SMS credit balance.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        setting = SMSSetting.load()
        return Response({
            "client": str(request.tenant),
            "sms_enabled": setting.sms_enabled if setting else False,
            "sms_credit": setting.sms_credit if setting else 0,
        })


class AllTenantSMSSettingView(APIView):
    """
    Get SMS settings for all tenants.
    Only accessible to superusers (global admins).
    """

    pagination_class = CustomPagination

    def get(self, request):
        search_query = request.query_params.get("search", None)
        tenants = Client.objects.exclude(schema_name="public").order_by("-id")

        if search_query:
            tenants = tenants.filter(name__icontains=search_query)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(tenants, request)

        data = []
        target_tenants = page if page is not None else tenants

        for tenant in target_tenants:
            with schema_context(tenant.schema_name):
                setting = SMSSetting.load()
                data.append({
                    "tenant": tenant,
                    "sms_enabled": setting.sms_enabled,
                    "sms_credit": setting.sms_credit,
                    "delivery_sms_enabled": setting.delivery_sms_enabled,
                })

        serializer = TenantSMSSettingSerializer(data, many=True)

        if page is not None:
            return paginator.get_paginated_response(serializer.data)

        return Response(serializer.data)


class SendCustomSMSView(APIView):
    """
    Send custom SMS for an order replacing {{name}} placeholder with customer_name.
    """

    def get_authenticators(self):
        if self.request.method == "POST":
            return [TenantJWTAuthentication()]
        return []

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return super().get_permissions()

    def post(self, request, *args, **kwargs):
        serializer = SendCustomSMSSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order_id = serializer.validated_data.get("order_id")
        phone_number = serializer.validated_data.get("phone_number")
        message = serializer.validated_data["message"]

        if order_id:
            try:
                order = Order.objects.get(id=order_id)
            except Order.DoesNotExist:
                return Response(
                    {"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND
                )

            if not order.customer_phone:
                return Response(
                    {"error": "Order has no customer phone number."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Replace {{customer_name}} with customer_name
            customer_name = order.customer_name if order.customer_name else ""
            message = message.replace("{{customer_name}}", customer_name)
            phone_to_send = order.customer_phone
        else:
            if not phone_number:
                return Response(
                    {"error": "Either order_id or phone_number must be provided."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            phone_to_send = phone_number

        result = send_sms_test(to=phone_to_send, text=message)

        if result["success"]:
            # Optionally return the send history detail
            return Response(
                {
                    "success": True,
                    "message": "SMS sent successfully.",
                    "details": result,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {"success": False, "error": result.get("error", "Failed to send SMS")},
            status=status.HTTP_400_BAD_REQUEST,
        )
