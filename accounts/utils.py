from django.utils.text import slugify
from django_tenants.utils import schema_context
from rest_framework_simplejwt.tokens import RefreshToken

from tenants.models import Client, Domain
from website.models import Page


def generate_fresh_tokens(user):
    is_onboarding_complete = getattr(user, "is_onboarding_complete", False)
    role = getattr(user, "role", "viewer")
    phone_number = getattr(user, "phone_number", "") or ""
    website_type = getattr(user, "website_type", "") or ""

    store_profile = user.owned_stores.first() or user.stores.first()
    has_profile = store_profile is not None

    store_name = ""
    has_profile_completed = False
    domain_name = ""
    sub_domain = ""
    is_first_login = False
    client = None

    if has_profile and store_profile:
        store_name = getattr(store_profile, "store_name", "") or ""
        owner = getattr(store_profile, "owner", None)
        sub_domain = slugify(store_name) if store_name else ""

        has_profile_completed = all([
            bool(getattr(store_profile, "logo", None)),
            bool(getattr(store_profile, "store_number", None)),
            bool(getattr(store_profile, "store_address", None)),
            bool(getattr(store_profile, "business_category", None)),
        ])

        if owner:
            client = Client.objects.filter(owner=owner).first()

            if client:
                domain = Domain.objects.filter(tenant=client, is_primary=True).first()

                domain_name = getattr(domain, "domain", "") if domain else ""

                is_template = getattr(client, "is_template_account", False)

                if not is_template:
                    schema_name = getattr(client, "schema_name", None)

                    if schema_name:
                        with schema_context(schema_name):
                            is_first_login = not Page.objects.exists()

    # Generate completely fresh refresh token
    refresh = RefreshToken.for_user(user)

    # Add latest claims from DB
    refresh["user_id"] = user.id
    refresh["email"] = user.email
    refresh["store_name"] = store_name
    refresh["has_profile"] = has_profile
    refresh["role"] = role
    refresh["phone_number"] = phone_number
    refresh["client_id"] = client.id if client else None
    refresh["domain"] = domain_name
    refresh["sub_domain"] = sub_domain
    refresh["has_profile_completed"] = has_profile_completed
    refresh["is_template_account"] = (
        getattr(client, "is_template_account", False) if client else False
    )
    refresh["first_login"] = is_first_login
    refresh["is_onboarding_complete"] = is_onboarding_complete
    refresh["website_type"] = website_type

    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


def log_user_activity(user, action, description, metadata=None):
    from .models import UserActivity

    UserActivity.objects.create(
        user=user, action=action, description=description, metadata=metadata or {}
    )
