import os
from datetime import datetime

import resend
from django.db import connection
from django.template.loader import render_to_string

from sales_crm.utils.email_service import get_email_common_context


def send_payment_success_emails(validated_data: dict) -> dict:
    """
    Service function to handle payment success email delivery to both customer and admin.
    Constructs tenant-aware from_email and admin_email, renders HTML templates,
    and sends emails via Resend API.
    """
    resend.api_key = os.getenv("RESEND_API_KEY")

    tenant = getattr(connection, "tenant", None)
    if tenant and hasattr(tenant, "name") and tenant.name:
        tenant_name = "".join(
            word.capitalize() for word in tenant.name.replace("-", " ").split()
        )
    else:
        tenant_name = "Nepdora"

    verified_sender = os.getenv(
        "DEFAULT_FROM_EMAIL_ADDRESS", "nepdora@baliyoventures.com"
    )
    from_email = f"{tenant_name} <{verified_sender}>"

    # Extract payment fields from validated data
    transaction_id = validated_data.get("transaction_id")
    amount = validated_data.get("amount")
    customer_email = validated_data.get("customer_email")
    customer_name = validated_data.get("customer_name") or "Valued Customer"
    customer_phone = validated_data.get("customer_phone", "")
    remarks = validated_data.get("remarks", "")
    payment_method = validated_data.get("payment_method") or "Online Payment"
    currency = validated_data.get("currency") or "NPR"
    payment_date = datetime.now().strftime("%B %d, %Y %I:%M %p")

    # Fetch admin email from tenant owner or override parameter
    admin_email = validated_data.get("admin_email")
    if (
        not admin_email
        and tenant
        and hasattr(tenant, "owner")
        and tenant.owner
        and tenant.owner.email
    ):
        admin_email = tenant.owner.email

    if not admin_email:
        common_context = get_email_common_context()
        admin_email = common_context.get("admin_email") or "nepdora@baliyoventures.com"

    context = {
        "tenant_name": tenant_name,
        "transaction_id": transaction_id,
        "amount": amount,
        "customer_name": customer_name,
        "customer_email": customer_email,
        "customer_phone": customer_phone,
        "remarks": remarks,
        "payment_method": payment_method,
        "currency": currency,
        "payment_date": payment_date,
        "admin_email": admin_email,
        "current_year": datetime.now().year,
    }

    results = {
        "customer_email_sent": False,
        "admin_email_sent": False,
        "errors": [],
    }

    # 1. Send Customer Confirmation Email
    if customer_email:
        try:
            customer_html = render_to_string(
                "mail/email/payment_success_customer.html", context
            )
            resend.Emails.send({
                "from": from_email,
                "to": customer_email,
                "subject": f"Payment Confirmation - {transaction_id} [{tenant_name}]",
                "html": customer_html,
            })
            results["customer_email_sent"] = True
            print(
                f"Payment confirmation email sent successfully to customer: {customer_email}"
            )
        except Exception as e:
            error_msg = f"Customer payment email delivery failed: {str(e)}"
            results["errors"].append(error_msg)
            print(error_msg)

    # 2. Send Admin Notification Email
    if admin_email:
        try:
            admin_html = render_to_string(
                "mail/email/payment_notification_admin.html", context
            )
            resend.Emails.send({
                "from": from_email,
                "to": admin_email,
                "subject": f"Payment Received Notification - {transaction_id} [{tenant_name}]",
                "html": admin_html,
            })
            results["admin_email_sent"] = True
            print(
                f"Admin payment notification email sent successfully to: {admin_email}"
            )
        except Exception as e:
            error_msg = f"Admin payment email delivery failed: {str(e)}"
            results["errors"].append(error_msg)
            print(error_msg)

    return results
