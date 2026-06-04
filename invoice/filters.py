import django_filters

from .models import Invoice


class InvoiceFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name="status", lookup_expr="icontains")
    customer_id = django_filters.NumberFilter(field_name="customer_id")
    start_date = django_filters.DateFilter(field_name="invoice_date", lookup_expr="gte")
    end_date = django_filters.DateFilter(field_name="invoice_date", lookup_expr="lte")

    class Meta:
        model = Invoice
        fields = ["status", "customer_id", "invoice_date"]
