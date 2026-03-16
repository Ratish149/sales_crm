import os

import resend
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from dotenv import load_dotenv
from rest_framework import filters, generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from sales_crm.pagination import CustomPagination

from .authentication import CustomerJWTAuthentication
from .models import Customer
from .serializers import (
    ChangePasswordSerializer,
    CustomerLoginSerializer,
    CustomerRegisterSerializer,
    CustomerSerializer,
)
from .tokens import customer_token_generator
from .utils import get_customer_from_request

load_dotenv()
resend.api_key = os.getenv("RESEND_API_KEY")


class CustomerRegisterView(generics.ListCreateAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerRegisterSerializer
    pagination_class = CustomPagination
    search_fields = ["first_name", "last_name", "email", "phone"]
    filter_backends = [filters.SearchFilter]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data.get("email")
        phone = serializer.validated_data.get("phone")
        
        customer = None
        if phone:
            customer = Customer.objects.filter(phone=phone).first()
        if not customer and email:
            customer = Customer.objects.filter(email=email).first()
            
        if customer:
            # Update existing customer
            for attr, value in serializer.validated_data.items():
                setattr(customer, attr, value)
            customer.save() # Model's save() handles password hashing
            return Response(self.get_serializer(customer).data, status=status.HTTP_200_OK)
        
        # Create new customer
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class CustomerRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerRegisterSerializer


class CustomerDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = CustomerSerializer
    authentication_classes = [CustomerJWTAuthentication]

    def get_object(self):
        customer = get_customer_from_request(self.request)
        if not customer:
            raise status.HTTP_401_UNAUTHORIZED
        return customer


class ChangePasswordView(APIView):
    authentication_classes = [CustomerJWTAuthentication]

    def post(self, request):
        customer = get_customer_from_request(request)
        if not customer:
            return Response(
                {
                    "error": "Authentication credentials were not provided or are invalid."
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            old_password = serializer.validated_data["old_password"]
            new_password = serializer.validated_data["new_password"]

            if not customer.check_password(old_password):
                return Response(
                    {"error": "Invalid old password."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            customer.password = new_password
            customer.save()  # defined save method hashes password
            return Response(
                {"message": "Password updated successfully."}, status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)





class CustomerRequestPasswordResetView(APIView):
    def post(self, request, *args, **kwargs):
        email = request.data.get("email")
        frontend_url = request.data.get("frontend_url")
        if not email:
            return Response(
                {"status": 400, "error": "Email is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            customer = Customer.objects.get(email=email)
        except Customer.DoesNotExist:
            # Do not reveal user existence
            return Response(
                {
                    "status": 200,
                    "message": "A password reset link has been sent",
                },
                status=status.HTTP_200_OK,
            )

        # Generate uid and token
        uid = urlsafe_base64_encode(force_bytes(customer.pk))
        token = customer_token_generator.make_token(customer)

        tenant_name = "".join(
            word.capitalize()
            for word in request.tenant.schema_name.replace("-", " ").split()
        )
        reset_link = f"{frontend_url}/customer/password/reset?uid={uid}&token={token}"



        # Context for your template
        context = {
            "user": customer,
            "password_reset_url": reset_link,
        }

        # Render HTML using your template
        html_body = render_to_string(
            "account/email/password_reset_message.html", context
        )
        subject = "Password Reset Requested"

        # Send email using Resend
        try:
            params = {
                "from": f"{tenant_name} <nepdora@baliyoventures.com>",
                "to": [email],
                "subject": subject,
                "html": html_body,
            }
            resend.Emails.send(params)
        except Exception:
            return Response(
                {"status": 500, "error": "Failed to send email"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "status": 200,
                "message": "If the email exists, a reset link has been sent",
            },
            status=status.HTTP_200_OK,
        )


class CustomerResetPasswordConfirmView(APIView):
    def post(self, request, *args, **kwargs):
        uidb64 = request.data.get("uid")
        token = request.data.get("token")
        new_password = request.data.get("password")

        if not uidb64 or not token or not new_password:
            return Response(
                {"status": 400, "error": "UID, token, and password are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Decode user ID
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            customer = Customer.objects.get(pk=uid)
        except (Customer.DoesNotExist, ValueError, TypeError):
            return Response(
                {"status": 400, "error": "Invalid UID"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate token
        if not customer_token_generator.check_token(customer, token):
            return Response(
                {"status": 400, "error": "Invalid or expired token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update password
        customer.password = new_password
        customer.save()

        return Response(
            {"status": 200, "message": "Password has been reset successfully"},
            status=status.HTTP_200_OK,
        )


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
        refresh["client_id"] = request.tenant.id
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
