import os
from datetime import datetime

import resend
from django.template.loader import render_to_string
from django_filters import rest_framework as django_filters
from rest_framework import generics
from rest_framework.pagination import PageNumberPagination

from .models import FAQ, Contact, FAQCategory, NepdoraTestimonial, Newsletter
from .serializers import (
    ContactSerializer,
    FAQCategorySerializer,
    FAQSerializer,
    NepdoraTestimonialSerializer,
    NewsletterSerializer,
)

# Initialize Resend
resend.api_key = os.getenv("RESEND_API_KEY")


# Create your views here.
class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class FAQCategoryListCreateView(generics.ListCreateAPIView):
    queryset = FAQCategory.objects.all()
    serializer_class = FAQCategorySerializer


class FAQCategoryRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = FAQCategory.objects.all()
    serializer_class = FAQCategorySerializer


class FAQFilterSet(django_filters.FilterSet):
    category = django_filters.CharFilter(field_name="category__id", lookup_expr="exact")

    class Meta:
        model = FAQ
        fields = {
            "category": ["exact"],
        }


class FAQListCreateView(generics.ListCreateAPIView):
    queryset = FAQ.objects.all()
    serializer_class = FAQSerializer
    filter_backends = [django_filters.DjangoFilterBackend]
    filterset_class = FAQFilterSet


class FAQRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = FAQ.objects.all()
    serializer_class = FAQSerializer


class NepdoraTestimonialListCreateView(generics.ListCreateAPIView):
    queryset = NepdoraTestimonial.objects.all()
    serializer_class = NepdoraTestimonialSerializer


class NepdoraTestimonialRetrieveUpdateDestroyView(
    generics.RetrieveUpdateDestroyAPIView
):
    queryset = NepdoraTestimonial.objects.all()
    serializer_class = NepdoraTestimonialSerializer


class ContactListCreateView(generics.ListCreateAPIView):
    queryset = Contact.objects.all().order_by("-created_at")
    serializer_class = ContactSerializer
    pagination_class = CustomPagination

    def perform_create(self, serializer):
        # Save the contact
        contact = serializer.save()

        # Send email notification to admin
        try:
            # Get current tenant name
            tenant_name = "Nepdora"

            # Prepare context
            context = {
                "name": contact.name,
                "email": contact.email,
                "phone_number": contact.phone_number,
                "message": contact.message,
                "tenant_name": tenant_name,
                "current_year": datetime.now().year,
            }

            # Render HTML
            html_content = render_to_string(
                "support/email/new_contact_notification.html", context
            )

            # Send via Resend to Admin
            resend.Emails.send({
                "from": f"{tenant_name} <nepdora@baliyoventures.com>",
                "to": "baliyotechnologies@gmail.com",
                "subject": f"New Contact Submission: {contact.name}",
                "html": html_content,
            })
            # --- Send Acknowledgment to User ---
            try:
                # Render Acknowledgment HTML
                user_html_content = render_to_string(
                    "support/email/contact_acknowledgment.html", context
                )

                resend.Emails.send({
                    "from": f"{tenant_name} <nepdora@baliyoventures.com>",
                    "to": contact.email,
                    "subject": "Thank you for contacting Nepdora",
                    "html": user_html_content,
                })
            except Exception as user_e:
                print(f"Failed to send acknowledgment email to user: {user_e}")

        except Exception as e:
            # Log error but don't fail the request
            print(f"Failed to send contact notification email: {e}")


class ContactRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer


class NewsletterListCreateView(generics.ListCreateAPIView):
    queryset = Newsletter.objects.all()
    serializer_class = NewsletterSerializer
    pagination_class = CustomPagination


class NewsletterRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Newsletter.objects.all()
    serializer_class = NewsletterSerializer
