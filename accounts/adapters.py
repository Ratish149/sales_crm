from allauth.headless.adapter import DefaultHeadlessAdapter
from allauth.account.adapter import DefaultAccountAdapter
from django.core.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken
from typing import Dict, Any
from allauth.account.utils import user_display, user_username, user_field, user_email
from allauth.account.models import EmailAddress
from accounts.models import CustomUser, StoreProfile
import re
import os
import resend
from django.template.loader import render_to_string
from dotenv import load_dotenv
from tenants.models import Client, Domain


class CustomHeadlessAdapter(DefaultHeadlessAdapter):
    """
    Custom headless adapter that extends DefaultHeadlessAdapter to include token functionality.
    """

    def serialize_user(self, user) -> Dict[str, Any]:
        """
        Returns the basic user data. Note that this data is also exposed in
        partly authenticated scenario's (e.g. password reset, email
        verification).
        """

        ret = {
            "display": user_display(user),
            "has_usable_password": user.has_usable_password(),
        }
        if user.pk:
            ret["id"] = user.pk
            email = EmailAddress.objects.get_primary_email(user)
            if email:
                ret["email"] = email

            # Check if user has a profile created
            has_profile = False
            if user:
                has_profile = hasattr(user, 'store_profile')

        username = user_username(user)
        try:
            refresh = RefreshToken.for_user(user)
            refresh['email'] = user.email
            refresh['store_name'] = user.store_name
            refresh['has_profile'] = has_profile
            ret["access_token"] = str(refresh.access_token)
            ret["refresh_token"] = str(refresh)
        except Exception as e:
            print(f"Error creating token: {e}")
        if username:
            ret["username"] = username

        return ret


class CustomAccountAdapter(DefaultAccountAdapter):

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
        store_name = data.get("store_name", "")
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
            # Save the user first
            user.save()

            # Now create the store profile with the saved user
            if store_name:
                store_profile, _ = StoreProfile.objects.get_or_create(
                    user=user)
               # In your CustomAccountAdapter.save_user method, add this check:
            schema_name = store_name

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
                domain=f"{schema_name}.127.0.0.1.nip.io:8000",
                tenant=tenant,
                is_primary=True,
            )
        return user


load_dotenv()

resend.api_key = os.getenv("RESEND_API_KEY")


class ResendEmailAdapter(DefaultAccountAdapter):
    def send_mail(self, template_prefix, email, context):
        try:
            print("context", context)
            html_body = render_to_string(
                "account/email/email_confirmation_message.html", context)
            test_email = "sikchhu.baliyo@gmail.com"
            # For testing, send to the verified email address
            # In production, you would verify your domain and use your own domain

            params = {
                "from": "onboarding@resend.dev",
                "to": [test_email],  # Send to verified email for testing
                "subject": "Sales CRM - Email Verification",
                "html": html_body,
            }
            print(f"Sending email to: {test_email} (original: {email})")
            print(f"Email context: {context}")
            response = resend.Emails.send(params)
            print(f"Email sent successfully: {response}")

        except Exception as e:
            print(f"Error sending email: {e}")
            # Fallback to default email sending if Resend fails
            super().send_mail(template_prefix, email, context)
