from datetime import datetime

from django.template.loader import render_to_string
from django_filters import rest_framework as django_filters
from rest_framework import generics
from rest_framework.pagination import PageNumberPagination

from sales_crm.utils.email_service import send_resend_email

from .models import (
    FAQ,
    Contact,
    FAQCategory,
    NepdoraPopupForm,
    NepdoraTestimonial,
    Newsletter,
    Showcase,
    VideoTestimonial,
)
from .serializers import (
    ContactSerializer,
    FAQCategorySerializer,
    FAQSerializer,
    NepdoraPopupFormSerializer,
    NepdoraTestimonialSerializer,
    NewsletterSerializer,
    ShowcaseSerializer,
    VideoTestimonialSerializer,
)


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

        # Send email notifications
        try:
            # Prepare context using centralized utility
            context = {
                "name": contact.name,
                "email": contact.email,
                "phone_number": contact.phone_number,
                "message": contact.message,
                "current_year": datetime.now().year,
                "admin_email": "baliyotechnologies@gmail.com",
                "tenant_name": "Nepdora",
            }

            # Render HTML for Admin Notification
            admin_html = render_to_string(
                "support/email/new_contact_notification.html", context
            )

            # Send via Resend to Admin
            send_resend_email(
                context["admin_email"],
                f"New Contact Submission: {contact.name}",
                admin_html,
                from_email="Nepdora <nepdora@baliyoventures.com>",
            )

            # --- Send Acknowledgment to User ---
            try:
                # Render Acknowledgment HTML
                user_html = render_to_string(
                    "support/email/contact_acknowledgment.html", context
                )

                send_resend_email(
                    contact.email,
                    f"Thank you for contacting {context['tenant_name']}",
                    user_html,
                    from_email="Nepdora <nepdora@baliyoventures.com>",
                )
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


class ShowcaseListCreateView(generics.ListCreateAPIView):
    queryset = Showcase.objects.all().order_by("-created_at")
    serializer_class = ShowcaseSerializer
    pagination_class = CustomPagination


class ShowcaseRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Showcase.objects.all()
    serializer_class = ShowcaseSerializer


class VideoTestimonialListCreateView(generics.ListCreateAPIView):
    queryset = VideoTestimonial.objects.all().order_by("-created_at")
    serializer_class = VideoTestimonialSerializer
    pagination_class = CustomPagination


class VideoTestimonialRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = VideoTestimonial.objects.all()
    serializer_class = VideoTestimonialSerializer


class NepdoraPopupFormListCreateView(generics.ListCreateAPIView):
    queryset = NepdoraPopupForm.objects.all().order_by("-created_at")
    serializer_class = NepdoraPopupFormSerializer
    pagination_class = CustomPagination

    def perform_create(self, serializer):
        # Save the form
        popup_form = serializer.save()

        # Send email notifications
        try:
            # Prepare context
            context = {
                "name": popup_form.name,
                "email": popup_form.email,
                "phone_number": popup_form.phone_number,
                "message": popup_form.message,
                "website_type": popup_form.website_type,
                "current_year": datetime.now().year,
                "admin_email": "baliyotechnologies@gmail.com",
                "tenant_name": "Nepdora",
            }

            # Render HTML for Admin Notification
            admin_html = render_to_string(
                "support/email/new_contact_notification.html", context
            )

            # Send via Resend to Admin
            send_resend_email(
                context["admin_email"],
                f"New Popup Form Submission: {popup_form.name}",
                admin_html,
                from_email="Nepdora <nepdora@baliyoventures.com>",
            )

            # --- Send Acknowledgment to User ---
            try:
                # Render Acknowledgment HTML
                if popup_form.email:
                    user_html = render_to_string(
                        "support/email/contact_acknowledgment.html", context
                    )

                    send_resend_email(
                        popup_form.email,
                        f"Thank you for contacting {context['tenant_name']}",
                        user_html,
                        from_email="Nepdora <nepdora@baliyoventures.com>",
                    )
            except Exception as user_e:
                print(f"Failed to send acknowledgment email to user: {user_e}")

        except Exception as e:
            # Log error but don't fail the request
            print(f"Failed to send popup form notification email: {e}")


class NepdoraPopupFormRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = NepdoraPopupForm.objects.all()
    serializer_class = NepdoraPopupFormSerializer
