import os
from datetime import datetime

import resend
from django.template.loader import render_to_string
from django_filters import rest_framework as django_filters
from rest_framework import filters, generics
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated

from sales_crm.authentication import TenantJWTAuthentication
from website.models import SiteConfig

from .models import Appointment, AppointmentReason
from .serializers import AppointmentReasonSerializer, AppointmentSerializer

# Initialize Resend
resend.api_key = os.getenv("RESEND_API_KEY")


# Create your views here.
class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class AppointmentReasonListCreateView(generics.ListCreateAPIView):
    queryset = AppointmentReason.objects.all()
    serializer_class = AppointmentReasonSerializer


class AppointmentReasonRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = AppointmentReason.objects.all()
    serializer_class = AppointmentReasonSerializer
    authentication_classes = [TenantJWTAuthentication]
    permission_classes = [IsAuthenticated]


class AppointmentFilterSet(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name="status", lookup_expr="icontains")
    time = django_filters.TimeFilter(field_name="time", lookup_expr="icontains")
    date_from = django_filters.DateFilter(field_name="created_at", lookup_expr="gte")
    date_to = django_filters.DateFilter(field_name="created_at", lookup_expr="lte")

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

    class Meta:
        model = Appointment
        fields = ["status", "time", "date_from", "date_to"]


class AppointmentListCreateView(generics.ListCreateAPIView):
    queryset = Appointment.objects.all().order_by("-created_at")
    pagination_class = CustomPagination
    serializer_class = AppointmentSerializer
    filter_backends = [django_filters.DjangoFilterBackend, filters.SearchFilter]
    filterset_class = AppointmentFilterSet
    search_fields = ["full_name", "phone_number"]

    def get_authenticators(self):
        if self.request.method == "GET":
            return [TenantJWTAuthentication()]
        return []  # No authentication for GET

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return super().get_permissions()

    def perform_create(self, serializer):
        # Save the appointment
        appointment = serializer.save()

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
                "full_name": appointment.full_name,
                "email": appointment.email,
                "phone": appointment.phone,
                "message": appointment.message,
                "date": appointment.date,
                "time": appointment.time,
                "reason": appointment.reason.name if appointment.reason else None,
                "tenant_name": tenant_name,
                "store_name": store_name,
                "current_year": datetime.now().year,
                "logo_url": logo_url,
            }

            # Render Admin Notification HTML
            admin_html_content = render_to_string(
                "appointment/email/appointment_notification.html", context
            )

            # Send via Resend to Admin
            if admin_email:
                resend.Emails.send({
                    "from": f"{store_name} <nepdora@baliyoventures.com>",
                    "to": admin_email,
                    "subject": f"New Appointment Request: {appointment.full_name}",
                    "html": admin_html_content,
                })

            # --- Send Acknowledgment to User ---
            try:
                # Render User Acknowledgment HTML
                user_html_content = render_to_string(
                    "appointment/email/appointment_acknowledgment.html", context
                )

                resend.Emails.send({
                    "from": f"{store_name} <nepdora@baliyoventures.com>",
                    "to": appointment.email,
                    "subject": f"Appointment Requested - {store_name}",
                    "html": user_html_content,
                })
            except Exception as user_e:
                print(
                    f"Failed to send appointment acknowledgment email to user: {user_e}"
                )

        except Exception as e:
            # Log error but don't fail the request
            print(f"Failed to send appointment notification email: {e}")


class AppointmentRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    authentication_classes = [TenantJWTAuthentication]
    permission_classes = [IsAuthenticated]
