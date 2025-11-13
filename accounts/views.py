import json
import os
from uuid import uuid4

import resend
from allauth.account.models import (
    EmailAddress,
    EmailConfirmation,
    EmailConfirmationHMAC,
)
from allauth.account.utils import (
    send_email_confirmation,
    user_email,
    user_field,
    user_username,
)
from django.db import connection
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
from dotenv import load_dotenv
from rest_framework import generics, permissions, serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from pricing.models import Pricing
from sales_crm.utils.error_handler import (
    ErrorCode,
    bad_request,
    duplicate_entry,
    not_found,
    server_error,
    validation_error,
)
from tenants.models import Client, Domain

from .models import CustomUser, Invitation, StoreProfile
from .serializers import (
    AcceptInvitationSerializer,
    InvitationSerializer,
    StoreProfileSerializer,
    UserWithStoresSerializer,
)

load_dotenv()
# Create your views here.

backend_url = os.getenv("BACKEND_URL")
frontendUrl = os.getenv("FRONTEND_URL")


@method_decorator(csrf_exempt, name="dispatch")
class CustomSignupView(APIView):
    def post(self, request, *args, **kwargs):
        # Parse request data
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            data = request.data
        except Exception as e:
            return bad_request(
                message="Invalid request data",
                code=ErrorCode.BAD_REQUEST,
                params={"error": str(e)},
            )

        email = data.get("email")
        store_name = data.get("store_name", "").lower()
        username = data.get("username", email)
        password = data.get("password1") or data.get("password")
        phone_number = data.get("phone")
        is_template_account = data.get("is_template_account", False)

        # Validate required fields
        if not email:
            return bad_request("Email is required")

        if not password:
            return bad_request("Password is required")

        # Check if username/email already exists
        if CustomUser.objects.filter(Q(username=username) | Q(email=email)).exists():
            return duplicate_entry(
                message="A user with this email/username already exists. Please use a different email or try logging in.",
                params={"email": email},
            )

        # Validate unique store_name schema

        try:
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
            if store_name:
                if Client.objects.filter(schema_name=store_name).exists():
                    return validation_error(
                        message=f"Store name '{store_name}' is already taken.",
                        params={"store_name": "This store name is already taken"},
                    )
                if store_name in ["public", "default", "postgres"]:
                    return validation_error(
                        message=f"Store name '{store_name}' is reserved.",
                        params={"store_name": "This store name is reserved"},
                    )

            # Create StoreProfile & Tenant
            if storeName:
                try:
                    frontend_url = f"{storeName}.{frontendUrl}"
                    user.frontend_url = frontend_url
                    user.save()
                    store_profile, created = StoreProfile.objects.get_or_create(
                        owner=user, store_name=store_name
                    )
                    user.role = "owner" if created else "viewer"
                    user.save()

                    tenant = Client.objects.create(
                        schema_name=storeName,
                        name=storeName,
                        owner=user,
                        is_template_account=is_template_account,
                    )
                    EmailAddress.objects.create(
                        email=user.email,
                        user=user,
                        primary=True,
                        verified=is_template_account,
                    )
                    Domain.objects.create(
                        domain=f"{storeName}.{backend_url}",
                        tenant=tenant,
                        is_primary=True,
                    )

                    # For template accounts, assign a premium plan with no expiration
                    if is_template_account:
                        # Get the first available premium plan
                        premium_plan = Pricing.objects.filter(
                            plan_type="premium"
                        ).first()
                        if premium_plan:
                            tenant.pricing_plan = premium_plan
                            tenant.paid_until = None  # No expiration
                            tenant.save()

                except Exception as e:
                    # Clean up user if tenant creation fails
                    user.delete()
                    return server_error(
                        message="Failed to create store profile",
                        params={"error": str(e)},
                    )

            # Send verification email
            try:
                send_email_confirmation(request, user)
            except Exception as e:
                # Log the error but don't fail the signup
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send verification email: {str(e)}")

            # Return success response
            return Response(
                {
                    "id": user.id,
                    "email": email,
                    "username": username,
                    "store_name": store_name,
                    "role": user.role,
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return server_error(
                message="An unexpected error occurred during signup",
                params={"error": str(e)},
            )


class CustomVerifyEmailView(APIView):
    """
    Verify email using the key sent in email.
    Accepts the key as query param (?key=) or in header 'x-email-verification-key'.
    """

    def post(self, request, *args, **kwargs):
        key = (
            request.query_params.get("key")
            or request.headers.get("x-email-verification-key")
            or request.data.get("key")
        )

        if not key:
            return bad_request(
                message="Verification key is required.",
                code=status.HTTP_400_BAD_REQUEST,
            )

        # Try to find EmailConfirmation by key (DB or HMAC)
        email_confirmation = EmailConfirmationHMAC.from_key(key)
        if not email_confirmation:
            try:
                email_confirmation = EmailConfirmation.objects.get(key=key.lower())
            except EmailConfirmation.DoesNotExist:
                return not_found(
                    message="Invalid verification key.", code=status.HTTP_404_NOT_FOUND
                )

        try:
            # Confirm email
            email_confirmation.confirm(request)
            return Response(
                {
                    "message": "Email verified successfully.",
                    "status": status.HTTP_200_OK,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return server_error(
                message="Failed to verify email",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                params={"error": str(e)},
            )


class ChangePasswordView(APIView):
    def post(self, request):
        password = request.data.get("password")
        email = request.data.get("email")
        user = CustomUser.objects.get(email=email)
        user.set_password(password)
        user.save()
        return Response(
            {"message": "Password changed successfully"}, status=status.HTTP_200_OK
        )


class ResendEmailVerificationView(APIView):
    def post(self, request):
        email = request.data.get("email")
        user = CustomUser.objects.get(email=email)
        if (
            user.is_authenticated
            and not user.emailaddress_set.filter(verified=True).exists()
        ):
            send_email_confirmation(request, user)
            return Response({"detail": "Verification email sent."})
        return Response(
            {"detail": "Already verified or not authenticated."},
            status=status.HTTP_400_BAD_REQUEST,
        )


class InvitationCreateView(generics.ListCreateAPIView):
    serializer_class = InvitationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Invitation.objects.filter(invited_by=self.request.user)

    def perform_create(self, serializer):
        # Get the store that the current user is inviting to
        # Assuming user can only own one store for now
        store = self.request.user.owned_stores.first()

        if not store:
            raise serializers.ValidationError(
                "You don't own any store to invite users to."
            )

        # Check if the user has permission to invite (only owner and admin can invite)
        if not (
            self.request.user.role in ["owner", "admin"]
            and store.owner == self.request.user
        ):
            raise PermissionDenied(
                "You don't have permission to invite users to this store."
            )

        email = serializer.validated_data["email"]
        role = serializer.validated_data["role"]

        # Check if user is already a member
        existing_user = CustomUser.objects.filter(email=email).first()
        if existing_user and store.users.filter(id=existing_user.id).exists():
            raise serializers.ValidationError(
                "This user is already a member of this store."
            )

        # Check for existing invitation
        if Invitation.objects.filter(email=email, store=store, accepted=False).exists():
            raise serializers.ValidationError(
                "An invitation has already been sent to this email."
            )
        # Create the invitation
        invitation = serializer.save(
            store=store, invited_by=self.request.user, role=role
        )

        # Send invitation email
        self._send_invitation_email(invitation)

    def _send_invitation_email(self, invitation):
        resend.api_key = os.getenv("RESEND_API_KEY")
        FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
        invite_url = f"{FRONTEND_URL}/user/invite/{invitation.token}"
        # Prepare email content using a template
        html_body = render_to_string(
            "account/email/invitation_message.html",
            {
                "store_name": invitation.store.store_name,
                "role": invitation.role,
                "invite_url": invite_url,
            },
        )
        params = {
            "from": "sales@baliyoventures.com",
            "to": [invitation.email],
            "subject": f"You are invited by {invitation.invited_by.email} to join {invitation.store.store_name}!",
            "html": html_body,
        }
        try:
            resend.Emails.send(params)
        except Exception as e:
            return server_error(
                message="Failed to send invitation email", params={"error": str(e)}
            )


class ResendInvitationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, invitation_id):
        try:
            invitation = Invitation.objects.get(
                id=invitation_id,
                store__users=request.user,  # Only allow resending if user has access to the store
                accepted=False,
            )

            # Check permission - only store owner or admin can resend invitations
            if not (
                request.user.role in ["owner", "admin"]
                and request.user in invitation.store.users.all()
            ):
                raise PermissionDenied(
                    "You don't have permission to resend this invitation."
                )

            # Update the token and save
            invitation.token = uuid4()
            invitation.save()

            # Send the invitation email
            InvitationCreateView._send_invitation_email(self, invitation)

            return Response(
                {"detail": "Invitation resent successfully."}, status=status.HTTP_200_OK
            )

        except Invitation.DoesNotExist:
            return Response(
                {"detail": "Invitation not found or already accepted."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AcceptInvitationView(APIView):
    def post(self, request):
        serializer = AcceptInvitationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"detail": "User created successfully."}, status=status.HTTP_201_CREATED
            )
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

    def get_queryset(self):
        # Users can only see stores they are members of
        return StoreProfile.objects.filter(owner=self.request.user)

    def get_object(self):
        # Get the store for the current user (assuming one store per user for now)
        store = self.request.user.owned_stores.first()
        if not store:
            store = self.request.user.stores.first()

        if not store:
            raise Http404("No store found for this user.")

        # Check if user has permission to view this store
        if (
            self.request.user not in store.users.all()
            and not self.request.user == store.owner
        ):
            raise PermissionDenied("You don't have permission to access this store.")

        return store

    def perform_update(self, serializer):
        # Only allow the store owner to update the store
        if self.request.user != serializer.instance.owner:
            raise PermissionDenied("Only the store owner can update store details.")
        serializer.save()

    def perform_destroy(self, instance):
        # Only allow the store owner to delete the store
        if self.request.user != instance.owner:
            raise PermissionDenied("Only the store owner can delete the store.")
        instance.delete()


class UserWithStoresListAPIView(generics.ListAPIView):
    serializer_class = UserWithStoresSerializer

    def get_queryset(self):
        return (
            CustomUser.objects.all()
            .prefetch_related("stores")  # prefetch many-to-many stores
            .prefetch_related("owned_stores")  # prefetch owned stores
        )


class DeleteUserAndSchemaView(APIView):
    """
    Delete user and their tenant schema.
    """

    def delete(self, request, user_id=None):
        # If you want only the logged-in user to delete themselves:
        user = get_object_or_404(CustomUser, id=user_id)

        # Check if this user owns a tenant
        try:
            client = Client.objects.get(owner=user)
        except Client.DoesNotExist:
            return Response(
                {"error": "This user does not own a tenant."},
                status=status.HTTP_404_NOT_FOUND,
            )

        schema_name = client.schema_name

        # 1️⃣ Drop tenant schema safely
        with connection.cursor() as cursor:
            cursor.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE;")

        # 2️⃣ Delete tenant object
        client.delete()

        # 3️⃣ Delete user
        user.delete()

        return Response(
            {"message": f"User and schema '{schema_name}' deleted successfully."},
            status=status.HTTP_200_OK,
        )
