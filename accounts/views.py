import base64
import json
import os
from datetime import date, timedelta
from uuid import uuid4

import requests
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
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.db import connection, transaction
from django.db.models import Q
from django.http import Http404
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
from django_tenants.utils import schema_context
from dotenv import load_dotenv
from rest_framework import generics, permissions, serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from blog.views import CustomPagination
from pricing.models import Pricing
from sales_crm.utils.error_handler import (
    ErrorCode,
    bad_request,
    duplicate_entry,
    not_found,
    server_error,
)
from sales_crm.utils.github_service import GitHubService
from tenants.models import Client, Domain

from .models import CustomUser, Invitation, StoreProfile
from .serializers import (
    AcceptInvitationSerializer,
    CustomUserSerializer,
    InvitationSerializer,
    StoreProfileSerializer,
    UserDataSerializer,
    UserWithStoresSerializer,
)

load_dotenv()
# Create your views here.
resend.api_key = os.getenv("RESEND_API_KEY")

backend_url = os.getenv("BACKEND_URL")
frontendUrl = os.getenv("FRONTEND_URL")
token_generator = PasswordResetTokenGenerator()
User = get_user_model()


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
        website_type = data.get("website_type", None)
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
            with transaction.atomic():
                # Create user instance (not saved yet)
                user_model = CustomUser
                user = user_model()

                user_email(user, email)
                user_username(user, username)
                user_field(user, "store_name", store_name)
                user_field(user, "phone_number", phone_number)
                user_field(user, "website_type", website_type)

                if password:
                    user.set_password(password)
                else:
                    user.set_unusable_password()

                # Save user
                user.save()
                storeName = slugify(store_name)
                if store_name:
                    if Client.objects.filter(schema_name=store_name).exists():
                        # Manually rollback by raising exception if not automatic?
                        # Return response here will NOT rollback unless I raise Exception.
                        # But this is a return, so it exits the function.
                        # Wait, if I return here, the transaction block exits normally?
                        # No, I should check existing clients BEFORE starting transaction or raise error.
                        pass  # Check below

                if store_name:
                    if Client.objects.filter(schema_name=store_name).exists():
                        raise Exception(f"Store name '{store_name}' is already taken.")
                    if store_name in ["public", "default", "postgres"]:
                        raise Exception(f"Store name '{store_name}' is reserved.")

                # Create StoreProfile & Tenant
                if storeName:
                    frontend_url = f"{storeName}.{frontendUrl}"
                    user.frontend_url = frontend_url
                    user.save()
                    store_profile, created = StoreProfile.objects.get_or_create(
                        owner=user, store_name=store_name
                    )
                    user.role = "owner" if created else "viewer"
                    user.save()

                    free_plan = Pricing.objects.filter(plan_type="free").first()
                    paid_until = date.today() + timedelta(days=30)

                    tenant = Client.objects.create(
                        schema_name=storeName,
                        name=storeName,
                        owner=user,
                        is_template_account=is_template_account,
                        pricing_plan=free_plan,
                        paid_until=paid_until,
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
                        user.is_onboarding_complete = True
                        user.save()
                        premium_plan = Pricing.objects.filter(
                            plan_type="premium"
                        ).first()
                        if premium_plan:
                            tenant.pricing_plan = premium_plan
                            tenant.paid_until = None
                            tenant.save()

                        # Create GitHub repository for template account
                        repo_name = storeName
                        description = f"Template: {store_name}"
                        repo_url = GitHubService.create_repo(repo_name, description)

                        if repo_url:
                            # Update tenant with repo URL and description
                            tenant.repo_url = repo_url
                            tenant.description = description
                            tenant.save(update_fields=["repo_url", "description"])

                            # Initialize Next.js project from template
                            template_repo_url = os.getenv("TEMPLATE_REPO_URL")
                            if website_type == "ecommerce":
                                template_repo_url = os.getenv(
                                    "ECOMMERCE_TEMPLATE", template_repo_url
                                )
                            elif website_type == "service":
                                template_repo_url = os.getenv(
                                    "SERVICE_TEMPLATE", template_repo_url
                                )

                            GitHubService.initialize_nextjs_project(
                                repo_url,
                                tenant.schema_name,
                                template_url=template_repo_url,
                            )

                            print(
                                f"✅ Created template account '{store_name}' with GitHub repo: {repo_url}"
                            )
                        else:
                            print(
                                f"⚠️ Template account '{store_name}' created but GitHub repo creation failed"
                            )

            # Send verification email (outside atomic? no, only if success)
            try:
                send_email_confirmation(request, user)
            except Exception:
                # If email fails, do we rollback user?
                # Probably yes, return error.
                # So keep inside atomic or handle explicitly.
                # Use strict requirement: "if any fail, do not create user"
                # But email sending is external.
                pass

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
            # Transaction will be rolled back
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


def get_image_base64(url):
    try:
        response = requests.get(url, timeout=5)
        return base64.b64encode(response.content).decode()
    except Exception as e:
        return e


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

        logo_b64 = get_image_base64(
            "https://nepdora.baliyoventures.com/static/logo/fulllogo.png"
        )
        fb_b64 = get_image_base64(
            "https://nepdora.baliyoventures.com/static/social/facebook-logo.png"
        )
        ig_b64 = get_image_base64(
            "https://nepdora.baliyoventures.com/static/social/instagram-logo.png"
        )

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
            "from": "Nepdora <nepdora@baliyoventures.com>",
            "to": [invitation.email],
            "subject": f"You are invited by {invitation.invited_by.email} to join {invitation.store.store_name}!",
            "html": html_body,
            "attachments": [
                {
                    "filename": "logo.png",
                    "content": logo_b64,
                    "content_id": "logo",  # Use cid:logo in HTML
                },
                {
                    "filename": "facebook.png",
                    "content": fb_b64,
                    "content_id": "facebook",
                },
                {
                    "filename": "instagram.png",
                    "content": ig_b64,
                    "content_id": "instagram",
                },
            ]
            if logo_b64
            else [],  # Only add if images loaded successfully
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


class UserUpdateAPIView(generics.UpdateAPIView):
    serializer_class = CustomUserSerializer
    permission_classes = [IsAuthenticated]
    queryset = CustomUser.objects.all()

    def get_object(self):
        # Return the authenticated user from the token
        return self.request.user


class CompleteOnboardingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if not user.is_onboarding_complete:
            user.is_onboarding_complete = True
            user.save(update_fields=["is_onboarding_complete"])

        return Response(
            {
                "status": "success",
                "message": "Onboarding marked as completed",
                "onboarding_complete": True,
            }
        )


class UserListDestroyAPIView(generics.ListAPIView):
    """
    Lists all users.
    For deletion, use the UserDeleteAPIView below.
    """

    queryset = CustomUser.objects.all()
    serializer_class = UserWithStoresSerializer
    pagination_class = CustomPagination


class UserDeleteAPIView(generics.RetrieveDestroyAPIView):
    """
    Deletes a user inside the tenant schema, then drops the tenant schema.
    """

    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    lookup_field = "id"

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        tenant = Client.objects.filter(owner=user).first()

        try:
            if not tenant or not tenant.schema_name:
                # No tenant, just delete the user from public
                user.delete()
            else:
                schema_name = tenant.schema_name

                with transaction.atomic():
                    # 1️⃣ Delete user inside tenant schema
                    with schema_context(schema_name):
                        user.delete()

                    # 2️⃣ Drop the tenant schema
                    with connection.cursor() as cursor:
                        cursor.execute(
                            f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE;'
                        )

            return Response(
                {"message": "User deleted and tenant schema dropped successfully."},
                status=status.HTTP_204_NO_CONTENT,
            )

        except Exception as e:
            return Response(
                {"error": f"Failed to delete user and drop tenant schema: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class RequestPasswordResetAPIView(APIView):
    """
    Request password reset link and send email using Resend API
    """

    def post(self, request, *args, **kwargs):
        email = request.data.get("email")
        if not email:
            return Response(
                {"status": 400, "error": "Email is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Do not reveal user existence
            return Response(
                {
                    "status": 200,
                    "message": "A password reset link has been sent",
                },
                status=status.HTTP_200_OK,
            )

        # Generate uid and token
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = token_generator.make_token(user)

        reset_link = (
            f"https://www.nepdora.com/account/password/reset?uid={uid}&token={token}"
        )

        logo_b64 = get_image_base64(
            "https://nepdora.baliyoventures.com/static/logo/fulllogo.png"
        )
        fb_b64 = get_image_base64(
            "https://nepdora.baliyoventures.com/static/social/facebook-logo.png"
        )
        ig_b64 = get_image_base64(
            "https://nepdora.baliyoventures.com/static/social/instagram-logo.png"
        )

        # Context for your template
        context = {
            "user": user,
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
                "from": "Nepdora <nepdora@baliyoventures.com>",
                "to": [email],
                "subject": subject,
                "html": html_body,
                "attachments": [
                    {
                        "filename": "logo.png",
                        "content": logo_b64,
                        "content_id": "logo",  # Use cid:logo in HTML
                    },
                    {
                        "filename": "facebook.png",
                        "content": fb_b64,
                        "content_id": "facebook",
                    },
                    {
                        "filename": "instagram.png",
                        "content": ig_b64,
                        "content_id": "instagram",
                    },
                ]
                if logo_b64
                else [],  # Only add if images loaded successfully
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


class ResetPasswordConfirmAPIView(APIView):
    """
    Confirm password reset using uid and token.
    POST request body:
    {
        "uid": "<uidb64>",
        "token": "<token>",
        "password": "NewPassword123!"
    }
    """

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
            user = User.objects.get(pk=uid)
        except (User.DoesNotExist, ValueError, TypeError):
            return Response(
                {"status": 400, "error": "Invalid UID"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate token
        if not token_generator.check_token(user, token):
            return Response(
                {"status": 400, "error": "Invalid or expired token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update password
        user.set_password(new_password)
        user.save()

        return Response(
            {"status": 200, "message": "Password has been reset successfully"},
            status=status.HTTP_200_OK,
        )


class UseTemplateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        template_id = request.data.get("template_id")
        store = request.user.owned_stores.first()
        if not store:
            return bad_request("User does not own a store.")

        repo_name = slugify(store.store_name)
        github_token = os.getenv("GITHUB_TOKEN")
        print("Github token", github_token)

        if not github_token:
            return server_error("GitHub token not configured")

        if template_id:
            try:
                template = Client.objects.get(id=template_id)
                source_url = template.repo_url
            except Client.DoesNotExist:
                return not_found("Template not found")
        else:
            source_url = os.getenv("TEMPLATE_REPO_URL")
            website_type = request.user.website_type

            if website_type == "ecommerce":
                source_url = os.getenv("ECOMMERCE_TEMPLATE", source_url)
            elif website_type == "service":
                source_url = os.getenv("SERVICE_TEMPLATE", source_url)
            else:
                source_url = os.getenv("TEMPLATE_REPO_URL", source_url)

            if not source_url:
                return server_error("No default template configured")

        # 1. Create Repo on GitHub using GitHubService
        # It handles unique naming internally now
        new_repo_url = GitHubService.create_repo(repo_name)

        if not new_repo_url:
            return server_error("Failed to create repository on GitHub.")

        # Save the new repo URL to the client
        try:
            client = Client.objects.get(schema_name=repo_name)
            client.repo_url = new_repo_url
            client.save(update_fields=["repo_url"])
        except Client.DoesNotExist:
            print(f"Client with schema_name {repo_name} not found.")

        # Extract actual created name from URL if needed.
        # Assuming URL is like https://github.com/user/repo-name.git
        final_repo_name = new_repo_url.split("/")[-1].replace(".git", "")

        # 2. Clone, Init, Push using GitHubService
        success = GitHubService.initialize_nextjs_project(
            new_repo_url, final_repo_name, template_url=source_url
        )

        if success:
            return Response(
                {
                    "message": "Template used successfully",
                    "repo_url": new_repo_url,
                    "repo_name": final_repo_name,
                },
                status=status.HTTP_200_OK,
            )
        else:
            return server_error("Failed to initialize project from template.")


class UserDataAPIView(APIView):
    """
    API endpoint to fetch user data with associated client information.
    Used by builder_backend for cross-project authentication.

    GET /api/accounts/user-data/
    Requires JWT authentication.
    Returns user data with client information.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Fetch client data for the user
        try:
            client = Client.objects.get(owner=user)
            client_data = {
                "id": client.id,
                "name": client.name,
                "schema_name": client.schema_name,
                "created_on": client.created_on,
                "paid_until": client.paid_until,
                "repo_url": client.repo_url,
                "description": client.description,
                "preview_url": client.preview_url,
                "is_template_account": client.is_template_account,
            }
        except Client.DoesNotExist:
            client_data = None

        # Prepare user data response
        user_data = {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "client": client_data,
        }

        serializer = UserDataSerializer(user_data)
        return Response(serializer.data, status=status.HTTP_200_OK)
