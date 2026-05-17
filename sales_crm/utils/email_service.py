import os
from datetime import datetime

import resend
from django.db import connection

from website.models import SiteConfig


def get_email_common_context():
    """
    Returns common context for emails including tenant and site configuration.
    """
    tenant = getattr(connection, "tenant", None)
    site_config = SiteConfig.objects.first()

    tenant_name = tenant.name if tenant else "Nepdora"

    # Try to get admin email from tenant owner first, then site config, then fallback
    admin_email = None
    if tenant and hasattr(tenant, "owner") and tenant.owner:
        admin_email = tenant.owner.email

    if not admin_email and site_config:
        admin_email = site_config.admin_email

    if not admin_email:
        admin_email = "nepdora@baliyoventures.com"

    return {
        "tenant_name": tenant_name,
        "store_name": tenant_name,  # Often used interchangeably
        "site_name": site_config.business_name if site_config else tenant_name,
        "logo_url": site_config.logo.url if site_config and site_config.logo else None,
        "admin_email": admin_email,
        "current_year": datetime.now().year,
        "year": datetime.now().year,
    }


def send_resend_email(to_emails, subject, html_content, from_email=None):
    """
    Sends an email using the Resend API.
    """
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        print("RESEND_API_KEY not found in environment variables.")
        return False

    resend.api_key = api_key

    if from_email is None:
        common_context = get_email_common_context()
        from_email = f"{common_context['tenant_name']} <nepdora@baliyoventures.com>"

    params = {
        "from": from_email,
        "to": to_emails if isinstance(to_emails, list) else [to_emails],
        "subject": subject,
        "html": html_content,
    }

    try:
        resend.Emails.send(params)
        print("Email sent successfully via Resend.")
        return True
    except Exception as e:
        print(f"Failed to send email via Resend: {str(e)}")
        return False
