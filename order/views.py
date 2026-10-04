import io
import logging
import os

from django.db.models import Prefetch, Sum
from django.http import FileResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django_filters import rest_framework as django_filters
from dotenv import load_dotenv
from drf_spectacular.utils import extend_schema, inline_serializer
from openpyxl import Workbook
from rest_framework import filters, generics, serializers, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from customer.authentication import CustomerJWTAuthentication
from customer.utils import get_customer_from_request
from logistics.models import Logistics
from sales_crm.authentication import TenantJWTAuthentication
from sales_crm.utils.s3bucket import PublicMediaStorage

from .models import Order, OrderItem, OrderItemImage
from .serializers import (
    AdminOrderSerializer,
    NCMCreateOrderSerializer,
    NCMWebhookSerializer,
    OrderListSerializer,
    OrderSerializer,
    SendOrderToNCMSerializer,
)
from .services.ncm_service import (
    create_direct_ncm_order,
    process_ncm_webhook,
    send_order_to_ncm,
)
from .utils import send_order_to_dash

# Optimized queryset for order listings and retrieval
ORDER_OPTIMIZED_QS = (
    Order.objects
    .select_related("customer", "promo_code")
    .prefetch_related(
        Prefetch(
            "items",
            queryset=OrderItem.objects.select_related(
                "product",
                "variant",
                "variant__product",
            ).prefetch_related("variant__option_values__option", "images"),
        )
    )
    .order_by("-created_at")
)

logger = logging.getLogger(__name__)

load_dotenv()
# Reusable function for Dash login
DASH_BASE_URL = os.getenv("DASH_BASE_URL")


class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class OrderFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name="status", lookup_expr="icontains")
    date_from = django_filters.DateFilter(field_name="created_at", lookup_expr="gte")
    date_to = django_filters.DateFilter(field_name="created_at", lookup_expr="lte")
    is_manual = django_filters.BooleanFilter(field_name="is_manual")
    pos_order = django_filters.BooleanFilter(field_name="pos_order")

    class Meta:
        model = Order
        fields = ["status", "date_from", "date_to", "is_manual", "pos_order"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        date_from = self.data.get("date_from")
        date_to = self.data.get("date_to")

        # If only date_from is provided, override the filter to get that exact date
        if date_from and not date_to:
            self.filters["date_from"].lookup_expr = "date"  # exact date
            # Optional: remove date_to filter if you want
            if "date_to" in self.filters:
                del self.filters["date_to"]


class OrderListCreateAPIView(generics.ListCreateAPIView):
    queryset = ORDER_OPTIMIZED_QS
    serializer_class = OrderSerializer
    pagination_class = CustomPagination
    authentication_classes = [CustomerJWTAuthentication]
    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
        django_filters.DjangoFilterBackend,
    ]
    search_fields = ["customer_name", "order_number", "customer_phone"]
    ordering_fields = ["created_at", "total_amount"]
    filterset_class = OrderFilter

    def get_serializer_class(self):
        if self.request.method == "GET":
            return OrderListSerializer
        return OrderSerializer


class AdminOrderListAPIView(generics.ListCreateAPIView):
    queryset = ORDER_OPTIMIZED_QS
    serializer_class = AdminOrderSerializer
    pagination_class = CustomPagination
    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
        django_filters.DjangoFilterBackend,
    ]
    authentication_classes = [TenantJWTAuthentication]
    permission_classes = [IsAuthenticated]
    search_fields = ["customer_name", "order_number", "customer_phone"]
    ordering_fields = ["created_at", "total_amount"]
    filterset_class = OrderFilter

    def get_serializer_class(self):
        if self.request.method == "GET":
            return OrderListSerializer
        return AdminOrderSerializer


class MyOrderListAPIView(generics.ListAPIView):
    queryset = ORDER_OPTIMIZED_QS
    serializer_class = OrderListSerializer
    pagination_class = CustomPagination
    authentication_classes = [CustomerJWTAuthentication]
    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
        django_filters.DjangoFilterBackend,
    ]
    search_fields = ["customer_name", "order_number", "customer_phone"]
    ordering_fields = ["created_at", "total_amount"]
    filterset_class = OrderFilter
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        customer = get_customer_from_request(self.request)
        if customer:
            from django.db.models import Q

            q_filter = Q(customer=customer)
            if customer.email:
                q_filter |= Q(customer_email=customer.email)
            if customer.phone:
                q_filter |= Q(customer_phone=customer.phone)

            return ORDER_OPTIMIZED_QS.filter(q_filter)
        return Order.objects.none()


# Retrieve, Update, Delete single Order


class OrderRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ORDER_OPTIMIZED_QS
    serializer_class = OrderSerializer
    authentication_classes = [TenantJWTAuthentication]

    def get_authenticators(self):
        request = getattr(self, "request", None)
        if request is None or request.method in ["PUT", "PATCH", "DELETE"]:
            return [TenantJWTAuthentication()]
        return []

    def get_permissions(self):
        request = getattr(self, "request", None)
        if request and request.method in ["PUT", "PATCH", "DELETE"]:
            return [IsAuthenticated()]
        return []

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        old_status = instance.status
        response = super().update(request, *args, **kwargs)

        # Refresh instance after update
        instance.refresh_from_db()
        new_status = instance.status

        # Handle transitions: deduct stock if changed from pending to any status other than pending or cancelled
        if old_status == "pending" and new_status not in ["pending", "cancelled"]:
            instance.deduct_stock()

        # Handle transitions: return stock if changed to pending or cancelled from any deducted state (non-pending and non-cancelled)
        if old_status not in ["pending", "cancelled"] and new_status in [
            "pending",
            "cancelled",
        ]:
            instance.return_stock()

        return response


class SendOrderToLogisticsAPIView(APIView):
    authentication_classes = [TenantJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            order = (
                Order.objects
                .select_related("customer", "promo_code")
                .prefetch_related(
                    Prefetch(
                        "items",
                        queryset=OrderItem.objects.select_related(
                            "product", "variant", "variant__product"
                        ),
                    )
                )
                .get(pk=pk)
            )
        except Order.DoesNotExist:
            return Response(
                {"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND
            )

        logistic_id = request.data.get("logistic")
        if not logistic_id:
            return Response(
                {"error": "logistic is required in post data"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            logistic_obj = Logistics.objects.get(id=logistic_id)
        except Logistics.DoesNotExist:
            return Response(
                {"error": "Logistics configuration not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not logistic_obj.is_enabled:
            return Response(
                {"error": f"{logistic_obj.logistic} logistics is not enabled"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if logistic_obj.logistic == "Dash":
            old_status = order.status
            res = send_order_to_dash(order)
            if res.status_code == 200:
                order.status = "shipped"
                order.save(update_fields=["status"])
                if old_status == "pending":
                    order.deduct_stock()
            return res
        elif logistic_obj.logistic == "NCM":
            extra_data = (
                request.data.copy()
                if hasattr(request.data, "copy")
                else dict(request.data)
            )
            location_name = (
                extra_data.get("branch")
                or extra_data.get("location_name")
                or extra_data.get("location")
                or getattr(order, "city", None)
            )
            if location_name:
                extra_data["branch"] = str(location_name).strip()
                if not order.city:
                    order.city = str(location_name).strip()
                    order.save(update_fields=["city"])

            if getattr(order, "is_paid", False) or str(
                extra_data.get("is_paid", "")
            ).lower() in ["true", "1", "yes"]:
                extra_data["cod_charge"] = "0"

            return send_order_to_ncm(
                order=order,
                extra_data=extra_data,
                logistic_obj=logistic_obj,
            )
        else:
            return Response(
                {"error": f"Unsupported logistic type: {logistic_obj.logistic}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class SendOrderToNCMAPIView(APIView):
    """
    Dedicated endpoint to send an order to Nepal Can Move (NCM).
    """

    authentication_classes = [TenantJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=SendOrderToNCMSerializer,
        responses={
            200: inline_serializer(
                name="NCMOrderSuccessResponse",
                fields={
                    "Message": serializers.CharField(),
                    "orderid": serializers.IntegerField(),
                },
            ),
            400: serializers.DictField(),
            404: serializers.DictField(),
        },
        description="Send an existing order to Nepal Can Move (NCM) logistics.",
    )
    def post(self, request, pk):
        try:
            order = (
                Order.objects
                .select_related("customer", "promo_code")
                .prefetch_related(
                    Prefetch(
                        "items",
                        queryset=OrderItem.objects.select_related(
                            "product", "variant", "variant__product"
                        ),
                    )
                )
                .get(pk=pk)
            )
        except Order.DoesNotExist:
            return Response(
                {"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = SendOrderToNCMSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        extra_data = serializer.validated_data.copy()
        location_name = (
            extra_data.get("branch")
            or extra_data.get("location_name")
            or extra_data.get("location")
            or getattr(order, "city", None)
        )
        if location_name:
            extra_data["branch"] = str(location_name).strip()
            if not order.city:
                order.city = str(location_name).strip()
                order.save(update_fields=["city"])

        if getattr(order, "is_paid", False) or extra_data.get("is_paid") is True:
            extra_data["cod_charge"] = "0"

        return send_order_to_ncm(
            order=order,
            extra_data=extra_data,
        )


class NCMCreateOrderAPIView(APIView):
    """
    Endpoint allowing vendors to directly create an order in Nepal Can Move (NCM).
    """

    authentication_classes = [TenantJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=NCMCreateOrderSerializer,
        responses={
            200: inline_serializer(
                name="NCMDirectOrderSuccessResponse",
                fields={
                    "Message": serializers.CharField(),
                    "orderid": serializers.IntegerField(),
                },
            ),
            400: serializers.DictField(),
        },
        description="Directly create an order in Nepal Can Move (NCM) with customer and delivery details.",
    )
    def post(self, request):
        serializer = NCMCreateOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return create_direct_ncm_order(validated_data=serializer.validated_data)


@extend_schema(
    operation_id="ncm_webhook_listener",
    request=NCMWebhookSerializer,
    responses={
        200: inline_serializer(
            name="NCMWebhookSuccessResponse",
            fields={
                "status": serializers.CharField(),
                "message": serializers.CharField(),
                "updated_orders": serializers.ListField(
                    child=serializers.DictField(), required=False
                ),
            },
        ),
        400: serializers.DictField(),
        404: serializers.DictField(),
    },
    description="Public webhook listener for Nepal Can Move (NCM) order updates with multi-tenant schema support.",
)
@method_decorator(csrf_exempt, name="dispatch")
class NCMWebhookAPIView(APIView):
    """
    Public webhook receiver for Nepal Can Move (NCM).
    Accepts status notifications (e.g. pickup_completed, sent_for_delivery, order_dispatched,
    order_arrived, delivery_completed) for single and bulk orders.
    Supports multi-tenancy via:
      - URL path schema_name: /api/order/ncm/webhook/<str:schema_name>/
      - Query param: ?schema_name=<schema_name>
      - Request payload key: {"schema_name": "<schema_name>"}
      - Domain tenant context
      - Cross-schema auto-detection
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, schema_name=None):
        """
        Supports ping / verification GET request from webhook setups.
        """
        resolved_schema = (
            schema_name
            or request.query_params.get("schema_name")
            or request.query_params.get("schema")
        )
        return Response(
            {
                "status": "active",
                "message": "NCM Webhook endpoint is active and listening.",
                "schema": resolved_schema,
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request, schema_name=None):
        resolved_schema = (
            schema_name
            or request.query_params.get("schema_name")
            or request.query_params.get("schema")
            or (
                request.data.get("schema_name")
                if isinstance(request.data, dict)
                else None
            )
        )
        payload = request.data if isinstance(request.data, dict) else {}

        status_code, response_data = process_ncm_webhook(
            data=payload,
            schema_name=resolved_schema,
            request_tenant=getattr(request, "tenant", None),
        )

        return Response(response_data, status=status_code)


class OrderGetAPIView(generics.RetrieveAPIView):
    queryset = ORDER_OPTIMIZED_QS
    serializer_class = OrderSerializer
    lookup_field = "order_number"


class OrderExcelExportView(generics.ListAPIView):
    queryset = ORDER_OPTIMIZED_QS
    serializer_class = AdminOrderSerializer
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = OrderFilter
    authentication_classes = [TenantJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        wb = Workbook()
        ws = wb.active
        ws.title = "Orders"

        headers = [
            "Order Number",
            "Customer Name",
            "Customer Email",
            "Customer Phone",
            "City",
            "Address",
            "Shipping Address",
            "Payment Type",
            "Status",
            "Total Amount",
            "Delivery Charge",
            "Is Paid",
            "Transaction ID",
            "Note",
            "Created At",
            "Product Name",
            "Variant",
            "Quantity",
            "Unit Price",
            "Item Total",
        ]

        for col, header in enumerate(headers, 1):
            ws.cell(row=1, column=col, value=header)

        current_row = 2
        for order in queryset:
            # Prefer Customer model details if available
            if order.customer:
                name = f"{order.customer.first_name} {order.customer.last_name}"
                email = order.customer.email
                phone = order.customer.phone
                address = order.customer.address
            else:
                name = order.customer_name
                email = order.customer_email
                phone = order.customer_phone
                address = order.customer_address

            # Base order info
            base_order_info = [
                order.order_number,
                name,
                email,
                phone,
                order.city,
                address,
                order.shipping_address,
                order.get_payment_type_display(),
                order.get_status_display(),
                float(order.total_amount),
                float(order.delivery_charge) if order.delivery_charge else 0.0,
                "Yes" if order.is_paid else "No",
                order.transaction_id,
                order.note,
                (
                    order.created_at.strftime("%Y-%m-%d %H:%M:%S")
                    if order.created_at
                    else ""
                ),
            ]

            items = list(order.items.all())

            for i, item in enumerate(items):
                row_data = [""] * len(headers)

                # Only add order info for the first item row
                if i == 0:
                    row_data[:15] = base_order_info

                # Item info
                product_name = (
                    item.product.name
                    if item.product
                    else (item.variant.product.name if item.variant else "Unknown")
                )
                variant_info = str(item.variant) if item.variant else ""

                row_data[15] = product_name
                row_data[16] = variant_info
                row_data[17] = item.quantity
                row_data[18] = float(item.price)
                row_data[19] = float(item.price * item.quantity)

                for col, value in enumerate(row_data, 1):
                    ws.cell(row=current_row, column=col, value=value)
                current_row += 1

        # Adjust column widths
        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except Exception:
                    pass
            adjusted_width = max_length + 2
            ws.column_dimensions[column].width = adjusted_width

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        filename = f"orders_export_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return FileResponse(
            buffer,
            as_attachment=True,
            filename=filename,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


class DashboardStatsView(APIView):
    authentication_classes = [TenantJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()

        # --- Base Global Metrics (excluding cancelled orders) ---
        base_qs = Order.objects.exclude(status="cancelled")

        total_orders = base_qs.count()
        total_revenue = base_qs.aggregate(Sum("total_amount"))["total_amount__sum"] or 0

        # --- Current Month Filtering Base (excluding cancelled orders) ---
        current_month_qs = base_qs.filter(
            created_at__year=now.year, created_at__month=now.month
        )

        total_orders_this_month = current_month_qs.count()
        revenue_this_month = (
            current_month_qs.aggregate(Sum("total_amount"))["total_amount__sum"] or 0
        )

        return Response({
            # All-Time Totals
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            # Current Month Context
            "total_orders_this_month": total_orders_this_month,
            "revenue_this_month": revenue_this_month,
        })


@extend_schema(
    responses={
        200: inline_serializer(
            name="MyOrderStatusResponse",
            fields={"status_counts": serializers.DictField()},
        )
    }
)
class MyOrderStatusView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomerJWTAuthentication]

    def get(self, request):
        customer = get_customer_from_request(request)
        if not customer:
            return Response({"error": "Customer not found"}, status=404)

        from django.db.models import Count

        user_orders = Order.objects.filter(customer=customer)
        counts = user_orders.values("status").annotate(count=Count("status"))

        status_counts = {s[0]: 0 for s in Order.ORDER_STATUS}
        for item in counts:
            status_counts[item["status"]] = item["count"]

        return Response(status_counts)


class CustomerOrderListAPIView(generics.ListAPIView):
    queryset = ORDER_OPTIMIZED_QS
    serializer_class = OrderListSerializer
    pagination_class = CustomPagination
    authentication_classes = [TenantJWTAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
        django_filters.DjangoFilterBackend,
    ]
    search_fields = ["customer_name", "order_number", "customer_phone"]
    ordering_fields = ["created_at", "total_amount"]
    filterset_class = OrderFilter

    def get_queryset(self):
        customer_id = self.request.query_params.get("customer_id")
        if not customer_id:
            return Order.objects.none()

        from django.db.models import Q

        from customer.models import Customer

        try:
            customer = Customer.objects.get(id=customer_id)
        except Customer.DoesNotExist:
            return Order.objects.none()

        q_filter = Q(customer=customer)
        if customer.email:
            q_filter |= Q(customer_email=customer.email)
        if customer.phone:
            q_filter |= Q(customer_phone=customer.phone)

        return ORDER_OPTIMIZED_QS.filter(q_filter)


class OrderStorageStatsView(APIView):
    # authentication_classes = [TenantJWTAuthentication]
    # permission_classes = [IsAuthenticated]

    def get(self, request):
        storage = PublicMediaStorage()

        item_image_count = 0
        item_image_bytes = 0

        use_s3_direct = False
        s3_objects = {}

        try:
            if hasattr(storage, "bucket") and storage.bucket:
                bucket = storage.bucket
                prefix = storage.location
                # List all objects in the prefix
                for obj in bucket.objects.filter(Prefix=prefix):
                    rel_path = obj.key[len(prefix) :]
                    s3_objects[rel_path] = obj.size
                use_s3_direct = len(s3_objects) > 0
        except Exception:
            pass

        def get_file_size(file_field):
            if not file_field:
                return 0
            name = file_field.name
            if use_s3_direct:
                return s3_objects.get(name, 0)
            try:
                if storage.exists(name):
                    return storage.size(name)
            except Exception:
                pass
            return 0

        # Order Item Images
        for item_img in OrderItemImage.objects.exclude(image="").only("image"):
            size = get_file_size(item_img.image)
            if size > 0:
                item_image_bytes += size
                item_image_count += 1

        def format_size(size_in_bytes):
            for unit in ["B", "KB", "MB", "GB", "TB"]:
                if size_in_bytes < 1024.0:
                    return f"{size_in_bytes:.2f} {unit}"
                size_in_bytes /= 1024.0
            return f"{size_in_bytes:.2f} PB"

        return Response({
            "status": "success",
            "data": {
                "order_item_images": {
                    "count": item_image_count,
                    "bytes": item_image_bytes,
                    "readable_size": format_size(item_image_bytes),
                }
            },
        })
