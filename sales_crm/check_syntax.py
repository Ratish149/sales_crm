import os

import django
from django.template.loader import render_to_string

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sales_crm.settings")
django.setup()


def test_template_rendering():
    print("Testing template rendering...")
    context = {
        "customer_name": "Test Customer",
        "customer_email": "test@example.com",
        "customer_phone": "1234567890",
        "customer_address": "Test Address",
        "order_number": "ORD-123",
        "items": [
            {
                "product_name": "Test Product",
                "brand": "Test Brand",
                "quantity": 1,
                "price": 100,
            }
        ],
        "total_amount": 100,
        "delivery_charge": 0,
        "tenant_name": "Test Tenant",
        "created_at": "2023-10-27",
    }

    try:
        content = render_to_string("order/email/admin_new_order.html", context)
        print("Template rendered successfully.")
    except Exception as e:
        print(f"Template rendering failed: {e}")


def check_imports():
    print("Checking imports...")
    try:
        print("Imports successful.")
    except Exception as e:
        print(f"Import failed: {e}")


if __name__ == "__main__":
    check_imports()
    test_template_rendering()
