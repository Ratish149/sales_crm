from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated

from sales_crm.authentication import TenantJWTAuthentication
from sales_crm.pagination import CustomPagination

from .filters import InvoiceFilter
from .models import Invoice
from .serializers import InvoiceSerializer


class InvoiceListCreateAPIView(generics.ListCreateAPIView):
    queryset = Invoice.objects.all().prefetch_related("items").order_by("-created_at")
    serializer_class = InvoiceSerializer
    authentication_classes = [TenantJWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = InvoiceFilter
    search_fields = ["bill_to_name", "bill_to_email", "invoice_number"]
    ordering_fields = ["invoice_date", "total_amount", "created_at"]


class InvoiceRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Invoice.objects.all().prefetch_related("items")
    serializer_class = InvoiceSerializer
    authentication_classes = [TenantJWTAuthentication]
    permission_classes = [IsAuthenticated]
