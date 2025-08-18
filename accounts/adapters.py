from allauth.headless.adapter import DefaultHeadlessAdapter
from allauth.account.adapter import DefaultAccountAdapter
from django.core.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken
from typing import Dict, Any
from allauth.account.utils import user_display, user_username, user_field, user_email
from allauth.account.models import EmailAddress
from accounts.models import StoreProfile
import re
import os
import resend
from django.template.loader import render_to_string
from dotenv import load_dotenv
from tenants.models import Client, Domain
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.utils import valid_email_or_none
from django.http import JsonResponse
from django.utils.text import slugify
load_dotenv()

resend.api_key = os.getenv("RESEND_API_KEY")
backend_url = os.getenv("BACKEND_URL")


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        """
        Hook that can be used to further populate the user instance.

        For convenience, we populate several common fields.

        Note that the user instance being populated represents a
        suggested User instance that represents the social user that is
        in the process of being logged in.

        The User instance need not be completely valid and conflict
        free. For example, verifying whether or not the username
        already exists, is not a responsibility.
        """
        email = data.get("email")
        store_name = data.get("store_name").lower()
        username = data.get("username", email)
        phone_number = data.get("phone")
        user = sociallogin.user
        user_username(user, username)
        user_email(user, valid_email_or_none(email) or "")
        user_field(user, "phone_number", phone_number)

        if store_name:
            store_profile, created = StoreProfile.objects.get_or_create(
                store_name=store_name)
            user.store = store_profile
            if created:
                user.role = "owner"
            else:
                user.role = "viewer"
            user.save()

            schema_name = store_name

            # Check if schema name already exists
            if Client.objects.filter(schema_name=schema_name).exists():
                raise ValidationError(
                    f"Store name '{store_name}' is already taken. Please choose a different name."
                )

            # Prevent schema from being a reserved word
            if schema_name in ['public', 'default', 'postgres']:
                schema_name = f"{schema_name}-user{user.id}"

            # Create tenant (Client)
            tenant = Client.objects.create(
                schema_name=schema_name,
                name=store_name,
                owner=user,
            )

            # Create domain for the tenant
            domain = Domain.objects.create(
                domain=f"{schema_name}.{backend_url}",
                tenant=tenant,
                is_primary=True,
            )
        else:
            user.save()
        return user


class CustomHeadlessAdapter(DefaultHeadlessAdapter):
    """
    Custom headless adapter that extends DefaultHeadlessAdapter to include token functionality.
    """

    def serialize_user(self, user) -> Dict[str, Any]:
        """
        Returns the basic user data along with JWT tokens and store info.
        """
        ret = {
            "display": user_display(user),
            "has_usable_password": user.has_usable_password(),
        }

        username = user_username(user)
        ret["username"] = username

        # Check if user has a store/profile
        has_profile = getattr(user, "store", None) is not None
        ret["has_profile"] = has_profile

        # Initialize extra variables
        domain_name = ""
        sub_domain = ""
        role = ""
        phone_number = ""
        store_name = ""
        has_profile_completed = False

        if has_profile:
            store_profile = user.store
            store_name = store_profile.store_name
            role = user.role
            phone_number = user.phone_number
            sub_domain = slugify(store_profile.store_name)

            # Check profile completion
            has_profile_completed = all([
                store_profile.logo,
                store_profile.store_number,
                store_profile.store_address,
                store_profile.business_category
            ])

            # Get tenant and domain safely
            try:
                client = Client.objects.get(owner=user)
                domain = Domain.objects.get(tenant=client)
                domain_name = domain.domain
            except Client.DoesNotExist:
                client = None
            except Domain.DoesNotExist:
                domain = None

        # Generate JWT tokens
        try:
            refresh = RefreshToken.for_user(user)
            refresh['email'] = user.email
            refresh['store_name'] = store_name
            refresh['has_profile'] = has_profile
            refresh['role'] = role
            refresh['phone_number'] = phone_number
            refresh['domain'] = domain_name
            refresh['sub_domain'] = sub_domain
            refresh['has_profile_completed'] = has_profile_completed

            ret["access_token"] = str(refresh.access_token)
            ret["refresh_token"] = str(refresh)
        except Exception as e:
            print(f"Error creating token: {e}")

        # Add store-related info
        ret.update({
            "store_name": store_name,
            "role": role,
            "phone_number": phone_number,
            "has_profile_completed": has_profile_completed,
        })

        return ret


class CustomAccountAdapter(DefaultAccountAdapter):

    def get_phone(self, user):
        """
        Return (phone_number, verified) tuple to satisfy Allauth's expectations.
        Always mark as verified since we don't require phone verification.
        """
        return getattr(user, 'phone_number', None), True

    def save_user(self, request, user, form, commit=True):
        """
        Saves a new User instance using information provided in the
        signup form.
        """
        import json

        # Parse the JSON data from request.body
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            # If request.body is already parsed (e.g. by middleware), use it directly
            data = request.body
        print('User adapter')
        print("data", data)
        # Default to learner if not specified
        email = data.get("email")
        store_name = data.get("store_name", "").lower()
        # Use email as username if not provided
        username = data.get("username", email)
        user_email(user, email)
        user_username(user, username)
        user_field(user, "store_name", store_name)

        if "password1" in data:
            user.set_password(data["password1"])
        elif "password" in data:
            user.set_password(data["password"])
        else:
            user.set_unusable_password()
        self.populate_username(request, user)

        if commit:
            user.save()

            if store_name:
                store_profile, created = StoreProfile.objects.get_or_create(
                    store_name=store_name)
                user.store = store_profile
                if created:
                    user.role = "owner"
                else:
                    user.role = "viewer"
                user.save()

                schema_name = store_name.slugify()

                # Check if schema name already exists
                if Client.objects.filter(schema_name=schema_name).exists():
                    raise ValidationError(
                        f"Store name '{store_name}' is already taken. Please choose a different name.")

                # Prevent schema from being a reserved word
                if schema_name in ['public', 'default', 'postgres']:
                    schema_name = f"{schema_name}-user{user.id}"

                    # Create tenant (Client)
                tenant = Client.objects.create(
                    schema_name=schema_name,
                    name=store_name,
                    owner=user,
                )

                # Create domain for the tenant
                domain = Domain.objects.create(
                    domain=f"{schema_name}.{backend_url}",
                    tenant=tenant,
                    is_primary=True,
                )
        return user

    def send_mail(self, template_prefix, email, context):
        try:

            if template_prefix == "account/email/password_reset_key":
                html_body = render_to_string(
                    "account/email/password_reset_message.html", context)
                subject = "Password Reset Requested"
            else:
                html_body = render_to_string(
                    "account/email/email_confirmation_message.html", context)
                subject = "Sales CRM - Email Verification"
            # test_email = "sikchhu.baliyo@gmail.com"
            # For testing, send to the verified email address
            # In production, you would verify your domain and use your own domain

            params = {
                "from": "nepdora@baliyoventures.com",
                "to": [email],  # Send to verified email for testing
                "subject": subject,
                "html": html_body,
            }

            response = resend.Emails.send(params)

        except Exception as e:
            # Fallback to default email sending if Resend fails
            super().send_mail(template_prefix, email, context)

    def respond_email_verification_sent(self, request, user):
        # Force session creation (even if not logged in yet)
        request.session.save()
        sessionid = request.session.session_key

        # Optionally log the user in here (if you want immediate session)
        # login(request, user)

        return JsonResponse({
            "status": 200,
            "data": {
                "message": "Verification mail sent successfully",
                "sessionid": sessionid
            }
        }, status=200)
