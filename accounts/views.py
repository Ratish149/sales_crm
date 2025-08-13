from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from allauth.account.models import EmailConfirmation, EmailConfirmationHMAC
from allauth.headless.account.views import SignupView as AllauthSignupView
from django.core.exceptions import ValidationError
from django.contrib.auth import login
from allauth.account import app_settings as allauth_settings
from allauth.account.utils import get_adapter, setup_user_email
from .serializers import AcceptInvitationSerializer, InvitationSerializer, StoreProfileSerializer
from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import CustomUser, StoreProfile
from allauth.account.utils import send_email_confirmation
import os
import resend
from django.template.loader import render_to_string
from dotenv import load_dotenv
from tenants.models import Client, Domain
import json
from allauth.account.adapter import get_adapter
from allauth.headless.account.views import SignupView as AllauthSignupView
from rest_framework_simplejwt.tokens import RefreshToken
from allauth.account.utils import user_email, user_username, user_field
from django.http import JsonResponse
from django.utils.text import slugify
load_dotenv()
# Create your views here.


@method_decorator(csrf_exempt, name='dispatch')
class CustomSignupView(APIView):

    def post(self, request, *args, **kwargs):
        # Parse request data
        try:
            data = json.loads(request.body)
        except Exception:
            data = request.data

        email = data.get("email")
        store_name = data.get("store_name", "").lower()
        username = data.get("username", email)
        password = data.get("password1") or data.get("password")
        phone_number = data.get("phone")

        # Validate unique store_name schema
        if store_name:
            if Client.objects.filter(schema_name=store_name).exists():
                return Response(
                    {"error": f"Store name '{store_name}' is already taken."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if store_name in ['public', 'default', 'postgres']:
                return Response(
                    {"error": f"Store name '{store_name}' is reserved."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Create user instance (not saved yet)
        user_model = CustomUser
        user = user_model()

        user_email(user, email)
        user_username(user, username)
        user_field(user, "store_name", store_name)
        user_field(user, "phone_number", phone_number)

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        # Save user
        user.save()
        storeName = slugify(store_name)

        # Create StoreProfile & Tenant
        if storeName:
            store_profile, created = StoreProfile.objects.get_or_create(
                store_name=storeName)
            user.store = store_profile
            user.role = "owner" if created else "viewer"
            user.save()

            tenant = Client.objects.create(
                schema_name=storeName,
                name=storeName,
                owner=user,
            )
            domain = Domain.objects.create(
                domain=f"{storeName}.127.0.0.1.nip.io",
                tenant=tenant,
                is_primary=True,
            )

        # Generate JWT tokens
        try:
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
        except Exception as e:
            return Response({"error": f"Token creation failed: {str(e)}"}, status=500)

        # Send verification email - optionally use adapter here or custom logic
        send_email_confirmation(request, user)

        # Return custom response including tokens and user info
        return Response({
            "id": user.id,
            "email": email,
            "username": username,
            "store_name": store_name,
            "role": user.role,
            "access_token": access_token,
            "refresh_token": refresh_token,
        }, status=201)


class CustomVerifyEmailView(APIView):
    """
    Verify email using the key sent in email.
    Accepts the key as query param (?key=) or in header 'x-email-verification-key'.
    """

    def post(self, request, *args, **kwargs):
        key = request.query_params.get(
            'key') or request.headers.get('x-email-verification-key') or request.data.get('key')

        if not key:
            return Response({"error": "Verification key is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Try to find EmailConfirmation by key (DB or HMAC)
        email_confirmation = EmailConfirmationHMAC.from_key(key)
        if not email_confirmation:
            try:
                email_confirmation = EmailConfirmation.objects.get(
                    key=key.lower())
            except EmailConfirmation.DoesNotExist:
                return Response({"error": "Invalid verification key."}, status=status.HTTP_400_BAD_REQUEST)

        # Confirm email
        email_confirmation.confirm(request)
        return Response({"message": "Email verified successfully."}, status=status.HTTP_200_OK)


class ChangePasswordView(APIView):
    def post(self, request):
        password = request.data.get('password')
        email = request.data.get('email')
        user = CustomUser.objects.get(email=email)
        user.set_password(password)
        user.save()
        return Response({'message': 'Password changed successfully'}, status=status.HTTP_200_OK)


class ResendEmailVerificationView(APIView):
    def post(self, request):
        email = request.data.get('email')
        user = CustomUser.objects.get(email=email)
        if user.is_authenticated and not user.emailaddress_set.filter(verified=True).exists():
            send_email_confirmation(request, user)
            return Response({"detail": "Verification email sent."})
        return Response({"detail": "Already verified or not authenticated."}, status=status.HTTP_400_BAD_REQUEST)


class InvitationCreateView(generics.CreateAPIView):
    serializer_class = InvitationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):

        resend.api_key = os.getenv("RESEND_API_KEY")
        invitation = serializer.save()
        FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
        invite_url = f"{FRONTEND_URL}/user/invite/{invitation.token}"
        # Prepare email content using a template
        html_body = render_to_string(
            "account/email/invitation_message.html",
            {"store_name": invitation.store.store_name,
                "role": invitation.role, "invite_url": invite_url}
        )
        params = {
            "from": "sales@baliyoventures.com",
            "to": [invitation.email],
            "subject": f"You are invited by {invitation.invited_by.email} to join {invitation.store.store_name}!",
            "html": html_body,
        }
        try:
            response = resend.Emails.send(params)
            print(f"Invitation email sent successfully: {response}")
        except Exception as e:
            print(f"Error sending invitation email: {e}")


class AcceptInvitationView(APIView):
    def post(self, request):
        serializer = AcceptInvitationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({'detail': 'User created successfully.'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StoreProfileView(generics.ListCreateAPIView):
    serializer_class = StoreProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        store_profile = serializer.save()
        # Assign the created store to the user if not already set
        if not request.user.store:
            request.user.store = store_profile
            request.user.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class StoreProfileDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = StoreProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        store_profile = StoreProfile.objects.filter(
            id=self.request.user.store_id).first()
        if not store_profile:
            raise Response({"detail": "Store profile not found."},
                           status=status.HTTP_404_NOT_FOUND)
        return store_profile

    def perform_update(self, serializer):
        instance = serializer.save()
        # Optionally, ensure the user's store is updated if needed
        if self.request.user.store_id != instance.id:
            self.request.user.store = instance
            self.request.user.save()
