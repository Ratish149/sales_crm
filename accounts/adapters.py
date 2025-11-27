import base64
import json
import os
from datetime import date, timedelta
from typing import Any, Dict

import requests
import resend
from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.models import EmailAddress
from allauth.account.utils import user_display, user_email, user_field, user_username
from allauth.headless.adapter import DefaultHeadlessAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model
from django.contrib.auth.models import update_last_login
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.utils.text import slugify
from django_tenants.utils import schema_context
from dotenv import load_dotenv
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import StoreProfile
from pricing.models import Pricing
from tenants.models import Client, Domain
from website.models import Page

load_dotenv()

resend.api_key = os.getenv("RESEND_API_KEY")
backend_url = os.getenv("BACKEND_URL")


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        """
        Invoked just after a user successfully authenticates via a social provider,
        but before the login is actually processed.
        """
        print(
            f"DEBUG: pre_social_login called. is_existing={sociallogin.is_existing}, user_authenticated={request.user.is_authenticated}"
        )

        # If social account already exists, allow.
        if sociallogin.is_existing:
            print("DEBUG: Social account exists. Allowing login.")
            return

        # If user is already logged in (connecting account), allow.
        if request.user.is_authenticated:
            print("DEBUG: User is authenticated. Allowing connection.")
            return

        # Check if this is a signup attempt (with store_name) or login attempt (without store_name)
        try:
            body = json.loads(request.body.decode("utf-8"))
            extra = body.get("data", {})
            store_name = extra.get("app", {}).get("store_name")
            print(f"DEBUG: store_name from request: {store_name}")
        except Exception as e:
            print(f"DEBUG: Error parsing request body: {e}")
            store_name = None

        # If a user with this email already exists, link the account and allow login.
        email = sociallogin.user.email
        print(f"DEBUG: Checking for existing user with email: {email}")
        if email:
            User = get_user_model()
            try:
                user = User.objects.get(email=email)
                print(
                    f"DEBUG: User found with email {email}. Auto-linking Google account."
                )
                sociallogin.connect(request, user)
                return
            except User.DoesNotExist:
                pass

        # If store_name is provided, this is a signup attempt - allow it to proceed
        if store_name:
            print(
                f"DEBUG: Signup attempt with store_name '{store_name}'. Allowing signup."
            )
            return

        # Otherwise, this is a login attempt without existing user - block it
        print(
            "DEBUG: No existing user found and no store_name provided. Blocking login."
        )
        raise ValidationError("Account does not exist. Please sign up first.")

    def populate_user(self, request, sociallogin, data):
        """Populate basic user fields only (no DB side-effects)."""
        user = sociallogin.user

        try:
            body = json.loads(request.body.decode("utf-8"))
            extra = body.get("data", {})
        except Exception as e:
            raise ValueError(f"Error parsing request body in populate_user: {e}")

        email = data.get("email")
        username = data.get("username", email)
        phone_number = extra.get("app", {}).get("phone")
        website_type = extra.get("app", {}).get("website_type") or "ecommerce"

        user_username(user, username)
        user_email(user, email or "")
        user_field(user, "phone_number", phone_number)
        user_field(user, "website_type", website_type)

        return user

    def save_user(self, request, sociallogin, form=None):
        """Called after the user is created in the main DB. Create tenant if needed."""
        user = super().save_user(request, sociallogin, form)

        try:
            body = json.loads(request.body.decode("utf-8"))
            extra = body.get("data", {})
        except Exception as e:
            raise ValueError(f"Error parsing request body in save_user: {e}")

        store_name = extra.get("app", {}).get("store_name")
        is_template_account = extra.get("is_template_account", False)

        if not store_name:
            return user

        store_name = store_name.lower()

        # Create or fetch StoreProfile
        store_profile, created = StoreProfile.objects.get_or_create(
            store_name=store_name, defaults={"owner": user}
        )

        if store_profile.owner == user:
            user.role = "owner"
        else:
            user.role = "viewer"
            store_profile.users.add(user)

        user.save()

        if created:
            schema_name = slugify(store_name)
            if Client.objects.filter(
                schema_name=schema_name
            ).exists() or schema_name in ["public", "default", "postgres"]:
                schema_name = f"{schema_name}-user{user.id}"

            free_plan = Pricing.objects.filter(plan_type="free").first()
            paid_until = date.today() + timedelta(days=30)

            tenant = Client.objects.create(
                schema_name=schema_name,
                name=schema_name,
                owner=user,
                is_template_account=is_template_account,
                pricing_plan=free_plan,
                paid_until=paid_until,
            )

            domain_url = f"{schema_name}.{backend_url}"
            Domain.objects.create(domain=domain_url, tenant=tenant, is_primary=True)

        return user


class CustomHeadlessAdapter(DefaultHeadlessAdapter):
    def serialize_user(self, user) -> Dict[str, Any]:
        ret: Dict[str, Any] = {
            "display": user_display(user),
            "has_usable_password": user.has_usable_password(),
            "username": user_username(user),
        }

        is_onboarding_complete = getattr(user, "is_onboarding_complete", False)
        store_profile = None
        has_profile = False
        domain_name = ""
        sub_domain = ""
        role = getattr(user, "role", "viewer")
        phone_number = getattr(user, "phone_number", "") or ""
        store_name = ""
        has_profile_completed = False
        owner = None
        is_first_login = False
        website_type = getattr(user, "website_type", "") or ""
        client = None
        domain = None

        try:
            store_profile = user.owned_stores.first() or user.stores.first()
            has_profile = store_profile is not None
        except Exception as e:
            raise ValueError(f"Error fetching store profile: {e}")

        if has_profile and store_profile:
            store_name = getattr(store_profile, "store_name", "") or ""
            owner = getattr(store_profile, "owner", None)
            sub_domain = slugify(store_name) if store_name else ""
            has_profile_completed = all(
                [
                    bool(getattr(store_profile, "logo", None)),
                    bool(getattr(store_profile, "store_number", None)),
                    bool(getattr(store_profile, "store_address", None)),
                    bool(getattr(store_profile, "business_category", None)),
                ]
            )

            try:
                if owner:
                    client = Client.objects.filter(owner=owner).first()
                    if client:
                        domain = Domain.objects.filter(
                            tenant=client, is_primary=True
                        ).first()
                        domain_name = getattr(domain, "domain", "") or ""
                        is_template = getattr(client, "is_template_account", False)
                        if is_template:
                            is_first_login = False
                        else:
                            schema_name = getattr(client, "schema_name", None)
                            if schema_name:
                                with schema_context(schema_name):
                                    is_first_login = not Page.objects.exists()
            except Exception as e:
                raise ValueError(f"Error fetching client/domain info: {e}")

        try:
            refresh = RefreshToken.for_user(user)
            is_template_flag = (
                getattr(client, "is_template_account", False) if client else False
            )

            refresh["email"] = user.email
            refresh["store_name"] = store_name
            refresh["has_profile"] = has_profile
            refresh["role"] = role
            refresh["phone_number"] = phone_number
            refresh["domain"] = domain_name
            refresh["sub_domain"] = sub_domain
            refresh["has_profile_completed"] = has_profile_completed
            refresh["is_template_account"] = is_template_flag
            refresh["first_login"] = is_first_login
            refresh["is_onboarding_complete"] = is_onboarding_complete
            refresh["website_type"] = website_type

            ret["access_token"] = str(refresh.access_token)
            ret["refresh_token"] = str(refresh)
            update_last_login(None, user)
        except Exception as e:
            raise ValueError(f"Error generating JWT token: {e}")

        ret.update(
            {
                "store_name": store_name,
                "role": role,
                "phone_number": phone_number,
                "domain": domain_name,
                "sub_domain": sub_domain,
                "has_profile_completed": has_profile_completed,
                "first_login": is_first_login,
                "is_onboarding_complete": is_onboarding_complete,
                "website_type": website_type,
            }
        )

        return ret


class CustomAccountAdapter(DefaultAccountAdapter):
    def get_phone(self, user):
        return getattr(user, "phone_number", None), True

    def save_user(self, request, user, form, commit=True):
        try:
            data = json.loads(request.body)
        except Exception:
            data = request.POST.dict() if hasattr(request, "POST") else {}

        email = data.get("email")
        store_name_raw = data.get("store_name", "") or ""
        store_name = store_name_raw.lower()
        username = data.get("username", email)
        is_template_account = data.get("is_template_account", False)

        user_email(user, email)
        user_username(user, username)

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
                schema_name = slugify(store_name)
                if Client.objects.filter(schema_name=schema_name).exists():
                    raise ValidationError(
                        f"Store name '{store_name}' is already taken."
                    )
                if schema_name in ["public", "default", "postgres"]:
                    schema_name = f"{schema_name}-user{user.id}"

                store_profile = StoreProfile.objects.create(
                    store_name=store_name, owner=user
                )
                user.role = "owner"
                user.save()

                tenant = Client.objects.create(
                    schema_name=schema_name,
                    name=store_name,
                    owner=user,
                    is_template_account=is_template_account,
                )

                EmailAddress.objects.create(
                    email=user.email,
                    user=user,
                    primary=True,
                    verified=is_template_account,
                )

                domain_url = f"{schema_name}.{backend_url}"
                Domain.objects.create(domain=domain_url, tenant=tenant, is_primary=True)

        return user

    def send_mail(self, template_prefix, email, context):
        try:
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

            def get_image_base64(url):
                try:
                    response = requests.get(url, timeout=5)
                    return base64.b64encode(response.content).decode()
                except Exception:
                    return None

            logo_b64 = get_image_base64(
                "https://nepdora.baliyoventures.com/static/logo/fulllogo.png"
            )
            fb_b64 = get_image_base64(
                "https://nepdora.baliyoventures.com/static/social/facebook-logo.png"
            )
            ig_b64 = get_image_base64(
                "https://nepdora.baliyoventures.com/static/social/instagram-logo.png"
            )

            attachments = (
                [
                    {"filename": "logo.png", "content": logo_b64, "content_id": "logo"},
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
                else []
            )

            resend.Emails.send(
                {
                    "from": "Nepdora <nepdora@baliyoventures.com>",
                    "to": [email],
                    "subject": subject,
                    "html": html_body,
                    "reply_to": "nepdora@gmail.com",
                    "attachments": attachments,
                }
            )

        except Exception:
            # Fallback to default email sending if Resend fails
            super().send_mail(template_prefix, email, context)

    def respond_email_verification_sent(self, request, user):
        request.session.save()
        sessionid = request.session.session_key

        return JsonResponse(
            {
                "status": 200,
                "data": {
                    "message": "Verification mail sent successfully",
                    "sessionid": sessionid,
                },
            },
            status=200,
        )
