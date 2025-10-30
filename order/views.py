import logging
import os

import requests
from django.db.models import Sum
from django.utils import timezone
from django_filters import rest_framework as django_filters
from dotenv import load_dotenv
from rest_framework import filters, generics
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from customer.utils import get_customer_from_request
from logistics.models import Logistics
from logistics.views import dash_login

from .models import Order, OrderItem
from .serializers import OrderListSerializer, OrderSerializer

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

    class Meta:
        model = Order
        fields = ["status", "date_from", "date_to", "is_manual"]

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
    queryset = Order.objects.all().order_by("-created_at")
    serializer_class = OrderSerializer
    pagination_class = CustomPagination
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


class MyOrderListAPIView(generics.ListAPIView):
    queryset = Order.objects.all().order_by("-created_at")
    serializer_class = OrderListSerializer
    pagination_class = CustomPagination
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
            return Order.objects.filter(customer=customer)
        return Order.objects.none()


# Retrieve, Update, Delete single Order


class OrderRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        old_status = instance.status
        response = super().update(request, *args, **kwargs)

        # Refresh instance after update
        instance.refresh_from_db()
        new_status = instance.status

        # Only trigger Dash API when status changes to "confirmed"
        if old_status != "confirmed" and new_status == "confirmed":
            dash_response = self._send_order_to_dash(instance)

            # If Dash failed, raise error and revert status
            if dash_response.status_code != 200:
                instance.status = old_status
                instance.save(update_fields=["status"])
                return dash_response  # Return Dash error directly

        return response

    def _send_order_to_dash(self, order):
        dash_obj = Logistics.objects.filter(is_enabled=True, logistic="Dash").first()
        print(dash_obj)

        if not dash_obj:
            return Response(
                {"error": "No active and enabled Dash logistics configuration found"},
                status=400,
            )

        # Handle token expiry
        token_expired = dash_obj.expires_at and dash_obj.expires_at <= timezone.now()
        if not dash_obj.access_token or token_expired:
            dash_obj.access_token = None
            dash_obj.refresh_token = None
            dash_obj.expires_at = None

            try:
                dash_obj.save()
                dash_obj, error = dash_login(
                    dash_obj.email, dash_obj.password, dash_obj=dash_obj
                )
                if not dash_obj:
                    return Response(
                        {"error": "Failed to refresh Dash token", "details": error},
                        status=400,
                    )
                dash_obj.refresh_from_db()
            except Exception as e:
                return Response(
                    {"error": f"Exception during Dash login: {str(e)}"}, status=500
                )

        access_token = dash_obj.access_token
        DASH_API_URL = f"{DASH_BASE_URL}/api/v1/clientOrder/add-order"
        HEADERS = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        }

        try:
            order = Order.objects.get(id=order.id)
        except Order.DoesNotExist:
            return Response(
                {"error": f"Order with id {order.id} does not exist."}, status=404
            )

        order_products = OrderItem.objects.filter(order=order)

        # Build product list
        product_name_list = []
        for op in order_products:
            try:
                if op.variant and hasattr(op.variant, "product"):
                    product_name = op.variant.product.name
                elif op.product:
                    product_name = op.product.name
                else:
                    product_name = "Unknown Product"
                product_name_list.append(f"{op.quantity}x {product_name}")
            except Exception:
                continue

        product_name = (
            ", ".join(product_name_list) if product_name_list else "No products"
        )
        product_price = order.total_amount
        full_address = getattr(order, "shipping_address", "No address provided")

        # Map payment type
        payment_type = (
            order.payment_type.lower() if order.payment_type else "cashOnDelivery"
        )
        if payment_type in ["cod", "cash_on_delivery"]:
            payment_type = "cashOnDelivery"
        elif payment_type in ["khalti", "esewa"]:
            payment_type = "prepaid"
        else:
            payment_type = "cashOnDelivery"

        receiver_location = getattr(order, "city", None) or "Kathmandu"

        customer = {
            "receiver_name": order.customer_name,
            "receiver_contact": order.customer_phone,
            "receiver_alternate_number": getattr(order, "alternate_phone", "") or "",
            "receiver_address": full_address,
            "receiver_location": receiver_location,
            "payment_type": payment_type,
            "product_name": product_name,
            "client_note": "",
            "receiver_landmark": getattr(order, "landmark", "") or "",
            "order_reference_id": str(order.order_number),
            "product_price": float(product_price) if product_price is not None else 0.0,
        }

        payload = {"customers": [customer]}
        print(payload)

        try:
            dash_response = requests.post(
                DASH_API_URL, json=payload, headers=HEADERS, timeout=30
            )
            print(dash_response)

            try:
                response_data = dash_response.json()
            except ValueError:
                return Response(
                    {
                        "error": "Invalid JSON response from Dash",
                        "status_code": dash_response.status_code,
                        "response_text": dash_response.text,
                    },
                    status=500,
                )

            if (
                dash_response.status_code != 200
                or response_data.get("status") != "success"
            ):
                return Response(
                    {
                        "error": "Failed to send order to Dash",
                        "dash_response": response_data,
                    },
                    status=dash_response.status_code or 500,
                )

            tracking_codes = []
            if response_data.get("data", {}).get("detail"):
                tracking_codes = [
                    {
                        "tracking_code": item.get("tracking_code"),
                        "order_reference_id": item.get("order_reference_id"),
                    }
                    for item in response_data["data"]["detail"]
                ]

            # ✅ Only update status if success & tracking code exists
            if tracking_codes:
                order.dash_tracking_code = tracking_codes[0]["tracking_code"]
                order.status = "shipped"
                order.save(update_fields=["dash_tracking_code", "status"])

                return Response(
                    {
                        "message": "Order sent to Dash successfully.",
                        "tracking_codes": tracking_codes,
                        "dash_response": response_data,
                    },
                    status=200,
                )

            return Response(
                {
                    "error": "Dash order creation returned no tracking code",
                    "dash_response": response_data,
                },
                status=500,
            )

        except requests.exceptions.RequestException as e:
            return Response(
                {"error": "Failed to connect to Dash API", "details": str(e)},
                status=500,
            )
        except Exception as e:
            import traceback

            traceback.print_exc()
            return Response(
                {"error": "An unexpected error occurred", "details": str(e)}, status=500
            )


class DashboardStatsView(APIView):
    def get(self, request):
        now = timezone.now()

        total_orders = Order.objects.count()
        total_orders_this_month = Order.objects.filter(
            created_at__year=now.year, created_at__month=now.month
        ).count()

        total_revenue = (
            Order.objects.aggregate(Sum("total_amount"))["total_amount__sum"] or 0
        )

        revenue_this_month = (
            Order.objects.filter(
                created_at__year=now.year, created_at__month=now.month
            ).aggregate(Sum("total_amount"))["total_amount__sum"]
            or 0
        )

        return Response(
            {
                "total_orders": total_orders,
                "total_orders_this_month": total_orders_this_month,
                "total_revenue": total_revenue,
                "revenue_this_month": revenue_this_month,
            }
        )


class MyOrderStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        customer = get_customer_from_request(request)
        if not customer:
            return Response({"error": "Customer not found"}, status=404)
        user_orders = Order.objects.filter(customer=customer)
        status_counts = {}
        for status, _ in Order.ORDER_STATUS:
            status_counts[status] = user_orders.filter(status=status).count()
        return Response(status_counts)
