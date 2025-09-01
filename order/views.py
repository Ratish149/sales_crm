from rest_framework import generics
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from .models import Order
from .serializers import OrderSerializer
from rest_framework.views import APIView
from django.utils import timezone
from rest_framework.response import Response
from django.db.models import Sum

# List and Create Orders
from rest_framework.pagination import PageNumberPagination

# Create your views here.


class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class OrderListCreateAPIView(generics.ListCreateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    pagination_class = CustomPagination

# Retrieve, Update, Delete single Order


class OrderRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer


class DashboardStatsView(APIView):
    def get(self, request):
        now = timezone.now()

        total_orders = Order.objects.count()
        total_orders_this_month = Order.objects.filter(
            created_at__year=now.year,
            created_at__month=now.month
        ).count()

        total_revenue = Order.objects.aggregate(
            Sum('total_amount')
        )['total_amount__sum'] or 0

        revenue_this_month = Order.objects.filter(
            created_at__year=now.year,
            created_at__month=now.month
        ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0

        return Response({
            "total_orders": total_orders,
            "total_orders_this_month": total_orders_this_month,
            "total_revenue": total_revenue,
            "revenue_this_month": revenue_this_month,

        })
