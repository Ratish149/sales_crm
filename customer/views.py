import os

import resend
from django.template.loader import render_to_string
from dotenv import load_dotenv
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Customer
from .serializers import CustomerLoginSerializer, CustomerRegisterSerializer

load_dotenv()
resend.api_key = os.getenv("RESEND_API_KEY")


def send_mail(template_prefix, email, context):
    if template_prefix == "account/email/password_reset_key":
        html_body = render_to_string(
            "account/email/password_reset_message.html", context
        )
        subject = "Password Reset Requested"
    else:
        html_body = render_to_string(
            "account/email/email_confirmation_message.html", context
        )
        subject = "Sales CRM - Email Verification"
    # test_email = "sikchhu.baliyo@gmail.com"
    # For testing, send to the verified email address
    # In production, you would verify your domain and use your own domain

    params = {
        "from": "Nepdora <nepdora@baliyoventures.com>",
        "to": [email],  # Send to verified email for testing
        "subject": subject,
        "html": html_body,
    }

    response = resend.Emails.send(params)


class CustomerRegisterView(generics.ListCreateAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerRegisterSerializer


class CustomerRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerRegisterSerializer


class CustomerLoginView(APIView):
    def post(self, request):
        serializer = CustomerLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        try:
            customer = Customer.objects.get(email=email)
        except Customer.DoesNotExist:
            return Response(
                {"error": "Invalid email or password"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not customer.check_password(password):
            return Response(
                {"error": "Invalid email or password"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Generate JWT tokens
        refresh = RefreshToken.for_user(customer)
        refresh["user_id"] = customer.id
        refresh["first_name"] = customer.first_name
        refresh["last_name"] = customer.last_name
        refresh["email"] = customer.email
        refresh["phone"] = customer.phone

        return Response(
            {
                "message": "Login successful",
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
            }
        )
