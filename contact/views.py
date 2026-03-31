import os
from datetime import datetime

import resend
from django.template.loader import render_to_string
from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated

from sales_crm.authentication import TenantJWTAuthentication
from sales_crm.utils.error_handler import (
    ErrorMessage,
    duplicate_entry,
    handle_transaction_errors,
)
from website.models import SiteConfig

from .models import Contact, NewsLetter
from .serializers import ContactSerializer, NewsLetterSerializer

# Initialize Resend
resend.api_key = os.getenv("RESEND_API_KEY")


class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class ContactCreateView(generics.ListCreateAPIView):
    queryset = Contact.objects.all().order_by("-created_at")
    serializer_class = ContactSerializer
    pagination_class = CustomPagination

    def get_authenticators(self):
        if self.request.method == "GET":
            return [TenantJWTAuthentication()]
        return []  # No authentication for GET

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return super().get_permissions()

    def perform_create(self, serializer):
        # Save the contact
        contact = serializer.save()

        # Send email notification to admin
        try:
            # Get current tenant
            tenant = getattr(self.request, "tenant", None)
            tenant_name = tenant.name if tenant else "Nepdora"
            admin_email = (
                tenant.owner.email
                if (tenant and hasattr(tenant, "owner") and tenant.owner)
                else None
            )

            # Get SiteConfig Logo
            logo_url = None
            store_name = tenant_name
            try:
                site_config = SiteConfig.objects.first()
                if site_config and site_config.logo:
                    logo_url = site_config.logo.url
            except Exception:
                pass

            # Prepare context
            context = {
                "name": contact.name,
                "email": contact.email,
                "phone_number": contact.phone_number,
                "message": contact.message,
                "tenant_name": tenant_name,
                "store_name": store_name,
                "current_year": datetime.now().year,
                "logo_url": logo_url,
            }

            # Render HTML
            html_content = render_to_string(
                "contact/email/new_contact_notification.html", context
            )

            # Send via Resend to Admin
            if admin_email:
                resend.Emails.send({
                    "from": f"{tenant_name} <nepdora@baliyoventures.com>",
                    "to": admin_email,
                    "subject": f"New Contact Submission: {contact.name}",
                    "html": html_content,
                })
            print(f"Contact notification email sent successfully to {admin_email}")

            # --- Send Acknowledgment to User ---
            try:
                # Render Acknowledgment HTML
                user_html_content = render_to_string(
                    "contact/email/contact_acknowledgment.html", context
                )

                resend.Emails.send({
                    "from": f"{tenant_name} <nepdora@baliyoventures.com>",
                    "to": contact.email,
                    "subject": f"Thank you for contacting {tenant_name}",
                    "html": user_html_content,
                })
                print(f"Acknowledgment email sent successfully to {contact.email}")
            except Exception as user_e:
                print(f"Failed to send acknowledgment email to user: {user_e}")

        except Exception as e:
            # Log error but don't fail the request
            print(f"Failed to send contact notification email: {e}")


class ContactRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    authentication_classes = [TenantJWTAuthentication]
    permission_classes = [IsAuthenticated]


class NewsLetterCreateView(generics.ListCreateAPIView):
    queryset = NewsLetter.objects.all().order_by("-created_at")
    serializer_class = NewsLetterSerializer
    pagination_class = CustomPagination

    def get_authenticators(self):
        if self.request.method == "GET":
            return [TenantJWTAuthentication()]
        return []  # No authentication for GET

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return super().get_permissions()

    @handle_transaction_errors
    def create(self, request, *args, **kwargs):
        email = request.data.get("email")
        if (
            email
            and NewsLetter.objects.filter(
                email__iexact=email, is_subscribed=True
            ).exists()
        ):
            return duplicate_entry(
                message=ErrorMessage.DUPLICATE_ENTRY,
                params={"email": "This email is already subscribed to the newsletter."},
            )
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        # Save the newsletter subscription
        newsletter = serializer.save()

        # Send email notifications
        try:
            # Get current tenant
            tenant = getattr(self.request, "tenant", None)
            tenant_name = tenant.name if tenant else "Nepdora"
            admin_email = (
                tenant.owner.email
                if (tenant and hasattr(tenant, "owner") and tenant.owner)
                else None
            )

            # Get SiteConfig Logo and store name
            logo_url = None
            store_name = tenant_name
            try:
                site_config = SiteConfig.objects.first()
                if site_config and site_config.logo:
                    logo_url = site_config.logo.url
            except Exception:
                pass

            # Prepare context
            context = {
                "email": newsletter.email,
                "tenant_name": tenant_name,
                "store_name": store_name,
                "current_year": datetime.now().year,
                "logo_url": logo_url,
            }

            # Render Admin Notification HTML
            admin_html_content = render_to_string(
                "contact/email/newsletter_notification.html", context
            )

            # Send via Resend to Admin
            if admin_email:
                resend.Emails.send({
                    "from": f"{store_name} <nepdora@baliyoventures.com>",
                    "to": admin_email,
                    "subject": f"New Newsletter Subscription: {newsletter.email}",
                    "html": admin_html_content,
                })
            print(f"Newsletter notification email sent successfully to {admin_email}")

            # --- Send Acknowledgment to User ---
            try:
                # Render User Acknowledgment HTML
                user_html_content = render_to_string(
                    "contact/email/newsletter_acknowledgment.html", context
                )

                resend.Emails.send({
                    "from": f"{store_name} <nepdora@baliyoventures.com>",
                    "to": newsletter.email,
                    "subject": f"Thank you for subscribing to {store_name}",
                    "html": user_html_content,
                })
                print(
                    f"Newsletter acknowledgment email sent successfully to {newsletter.email}"
                )
            except Exception as user_e:
                print(
                    f"Failed to send newsletter acknowledgment email to user: {user_e}"
                )

        except Exception as e:
            # Log error but don't fail the request
            print(f"Failed to send newsletter notification email: {e}")


class NewsLetterRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = NewsLetter.objects.all()
    serializer_class = NewsLetterSerializer
    authentication_classes = [TenantJWTAuthentication]
    permission_classes = [IsAuthenticated]
