import logging
import os

from django.db.models import Sum
from django.utils import timezone
from django_filters import rest_framework as django_filters
from dotenv import load_dotenv
from rest_framework import filters, generics
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from customer.authentication import CustomerJWTAuthentication
from customer.utils import get_customer_from_request

from .models import Order
from .serializers import OrderListSerializer, OrderSerializer
from .utils import send_order_to_dash

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
    authentication_classes = [JWTAuthentication, CustomerJWTAuthentication]
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
            dash_response = send_order_to_dash(instance)

            # If Dash failed, raise error and revert status
            if dash_response.status_code != 200:
                instance.status = old_status
                instance.save(update_fields=["status"])
                return dash_response  # Return Dash error directly

        return response


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
    authentication_classes = [CustomerJWTAuthentication]

    def get(self, request):
        customer = get_customer_from_request(request)
        if not customer:
            return Response({"error": "Customer not found"}, status=404)
        user_orders = Order.objects.filter(customer=customer)
        status_counts = {}
        for status, _ in Order.ORDER_STATUS:
            status_counts[status] = user_orders.filter(status=status).count()
        return Response(status_counts)
