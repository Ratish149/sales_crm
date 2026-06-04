from django.contrib import admin

from .models import Invoice, InvoiceItem


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_number",
        "bill_to_name",
        "invoice_date",
        "due_date",
        "status",
        "total_amount",
    )
    list_filter = ("status", "invoice_date", "due_date")
    search_fields = ("invoice_number", "bill_to_name", "bill_to_email")
    inlines = [InvoiceItemInline]
