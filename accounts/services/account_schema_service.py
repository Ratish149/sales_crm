import re
from typing import Any, Dict, Optional, Tuple

from django.conf import settings
from django.core.cache import cache
from django.db import connections, transaction
from django.utils.text import slugify
from django_tenants.utils import (
    get_tenant_database_alias,
    schema_exists,
)
from rest_framework.exceptions import NotFound, ValidationError

from accounts.models import CustomUser, StoreProfile
from accounts.utils import generate_fresh_tokens, log_user_activity
from tenants.models import Client, Domain

RESERVED_SCHEMAS = {
    "public",
    "default",
    "postgres",
    "information_schema",
    "pg_catalog",
    "template0",
    "template1",
}


def validate_schema_name(
    schema_name: str, current_client_id: Optional[int] = None
) -> str:
    """
    Validates that a schema name is safe, valid for PostgreSQL, not reserved,
    and not already used by another tenant or existing PostgreSQL schema.
    """
    cleaned_schema = slugify(schema_name.strip()).lower()

    if not cleaned_schema:
        raise ValidationError({"schema_name": "Schema name cannot be empty."})

    if len(cleaned_schema) > 63:
        raise ValidationError({
            "schema_name": "Schema name cannot exceed 63 characters."
        })

    if not re.match(r"^[a-z0-9][a-z0-9_-]*$", cleaned_schema):
        raise ValidationError({
            "schema_name": (
                "Schema name must start with an alphanumeric character and contain "
                "only lowercase letters, digits, underscores, or hyphens."
            )
        })

    if cleaned_schema in RESERVED_SCHEMAS or cleaned_schema.startswith("pg_"):
        raise ValidationError({
            "schema_name": f"Schema name '{cleaned_schema}' is reserved and cannot be used."
        })

    query = Client.objects.filter(schema_name=cleaned_schema)
    if current_client_id:
        query = query.exclude(pk=current_client_id)
    if query.exists():
        raise ValidationError({
            "schema_name": f"Schema name '{cleaned_schema}' is already taken by another store."
        })

    return cleaned_schema


def get_account_client_and_user(
    request_user: Optional[CustomUser] = None,
    target_user_id: Optional[int] = None,
    client_id: Optional[int] = None,
    email: Optional[str] = None,
) -> Tuple[Client, CustomUser]:
    """
    Resolves target Client and owner CustomUser.
    Lookup precedence: email -> client_id -> target_user_id -> request_user
    """
    if email:
        cleaned_email = email.strip().lower()
        try:
            target_user = CustomUser.objects.get(
                email__iexact=cleaned_email, is_deleted=False
            )
        except CustomUser.DoesNotExist:
            raise NotFound({"detail": f"User with email '{email}' does not exist."})

        client = Client.objects.filter(owner=target_user).first()
        if not client:
            raise NotFound({
                "detail": f"No tenant account found for user with email '{email}'."
            })
        return client, target_user

    if client_id is not None:
        try:
            client = Client.objects.select_related("owner").get(pk=client_id)
        except Client.DoesNotExist:
            raise NotFound({"detail": f"Client with ID {client_id} does not exist."})

        target_user = client.owner if client.owner else request_user
        if not target_user:
            raise NotFound({"detail": f"No owner found for client ID {client_id}."})
        return client, target_user

    if target_user_id is not None:
        try:
            target_user = CustomUser.objects.get(pk=target_user_id, is_deleted=False)
        except CustomUser.DoesNotExist:
            raise NotFound({"detail": f"User with ID {target_user_id} does not exist."})

        client = Client.objects.filter(owner=target_user).first()
        if not client:
            raise NotFound({
                "detail": f"No tenant account found for user ID {target_user_id}."
            })
        return client, target_user

    if request_user and getattr(request_user, "is_authenticated", False):
        client = Client.objects.filter(owner=request_user).first()
        if not client:
            raise NotFound({"detail": "No tenant account found for your user account."})
        return client, request_user

    raise ValidationError({"email": "Email is required to identify the account."})


def change_account_schema_and_store_name(
    request_user: Optional[CustomUser] = None,
    target_user_id: Optional[int] = None,
    client_id: Optional[int] = None,
    email: Optional[str] = None,
    new_schema_name: Optional[str] = None,
    new_store_name: Optional[str] = None,
    new_tenant_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Renames the PostgreSQL database schema and updates tenant name, store name, domains,
    and associated profile for a tenant account.
    """
    client, target_user = get_account_client_and_user(
        request_user=request_user,
        target_user_id=target_user_id,
        client_id=client_id,
        email=email,
    )

    old_schema = client.schema_name
    old_tenant_name = client.name
    store_profile = (
        StoreProfile.objects.filter(owner=target_user).first()
        or target_user.stores.first()
    )
    old_store_name = store_profile.store_name if store_profile else old_tenant_name

    # Determine resolved tenant name and store name
    resolved_tenant_name = None
    if new_tenant_name and new_tenant_name.strip():
        resolved_tenant_name = new_tenant_name.strip()
    elif new_store_name and new_store_name.strip():
        resolved_tenant_name = new_store_name.strip()
    elif new_schema_name and new_schema_name.strip():
        resolved_tenant_name = slugify(new_schema_name.strip()).lower()
    else:
        resolved_tenant_name = old_tenant_name

    resolved_store_name = None
    if new_store_name and new_store_name.strip():
        resolved_store_name = new_store_name.strip()
    elif new_tenant_name and new_tenant_name.strip():
        resolved_store_name = new_tenant_name.strip()
    else:
        resolved_store_name = old_store_name

    schema_changed = False
    cleaned_new_schema = old_schema

    if new_schema_name:
        cleaned_new_schema = validate_schema_name(
            schema_name=new_schema_name,
            current_client_id=client.id,
        )
        if cleaned_new_schema != old_schema:
            if schema_exists(cleaned_new_schema):
                raise ValidationError({
                    "schema_name": f"PostgreSQL database schema '{cleaned_new_schema}' already exists."
                })
            schema_changed = True

    tenant_name_changed = bool(resolved_tenant_name != old_tenant_name)
    store_name_changed = bool(resolved_store_name != old_store_name)

    if not schema_changed and not tenant_name_changed and not store_name_changed:
        return {
            "status": "success",
            "message": "No changes detected. Schema, tenant name, and store name remain unchanged.",
            "client_id": client.id,
            "tenant_name": client.name,
            "old_tenant_name": old_tenant_name,
            "new_tenant_name": client.name,
            "old_schema_name": old_schema,
            "new_schema_name": old_schema,
            "old_store_name": old_store_name,
            "new_store_name": old_store_name,
            "domains": list(
                Domain.objects.filter(tenant=client).values_list("domain", flat=True)
            ),
            "sub_domain": target_user.sub_domain or old_schema,
            "tokens": generate_fresh_tokens(target_user) if target_user else None,
        }

    # Ensure connection is in public schema before renaming PostgreSQL schema
    db_alias = get_tenant_database_alias()
    db_conn = connections[db_alias]
    db_conn.set_schema_to_public()

    old_domain_names = list(
        Domain.objects.filter(tenant=client).values_list("domain", flat=True)
    )

    with transaction.atomic():
        # 1. Rename PostgreSQL schema if schema name changed
        if schema_changed:
            if schema_exists(old_schema):
                with db_conn.cursor() as cursor:
                    cursor.execute(
                        f'ALTER SCHEMA "{old_schema}" RENAME TO "{cleaned_new_schema}"'
                    )
            else:
                with db_conn.cursor() as cursor:
                    cursor.execute(f'CREATE SCHEMA "{cleaned_new_schema}"')

            client.schema_name = cleaned_new_schema

        # 2. Update Client.name (Tenant Name)
        if resolved_tenant_name:
            client.name = resolved_tenant_name

        update_fields = []
        if schema_changed:
            update_fields.append("schema_name")
        if tenant_name_changed:
            update_fields.append("name")

        if update_fields:
            client.save(update_fields=update_fields)

        # 3. Update Domain records
        if schema_changed:
            domains = Domain.objects.filter(tenant=client)
            if domains.exists():
                for dom in domains:
                    if dom.domain.startswith(f"{old_schema}."):
                        suffix = dom.domain[len(old_schema) + 1 :]
                        dom.domain = f"{cleaned_new_schema}.{suffix}"
                        dom.save(update_fields=["domain", "updated_at"])
            else:
                backend_domain = getattr(settings, "BACKEND_DOMAIN", "localhost:8000")
                Domain.objects.create(
                    domain=f"{cleaned_new_schema}.{backend_domain}",
                    tenant=client,
                    is_primary=True,
                )

        # 4. Update CustomUser.sub_domain
        if schema_changed and target_user:
            target_user.sub_domain = cleaned_new_schema
            target_user.save(update_fields=["sub_domain"])

        # 5. Update StoreProfile.store_name
        final_store_name = resolved_store_name or old_store_name
        if resolved_store_name:
            if store_profile:
                store_profile.store_name = resolved_store_name
                store_profile.save(update_fields=["store_name", "updated_at"])
            elif target_user:
                store_profile = StoreProfile.objects.create(
                    owner=target_user,
                    store_name=resolved_store_name,
                )

    # Invalidate cache for tenant lookups
    cache.delete(f"tenant_sub:{old_schema}")
    cache.delete(f"tenant_sub:{cleaned_new_schema}")
    for d in old_domain_names:
        cache.delete(f"tenant_domain:{d}")

    # Log user activity
    activity_user = (
        request_user
        if (request_user and getattr(request_user, "is_authenticated", False))
        else target_user
    )
    if activity_user:
        log_user_activity(
            user=activity_user,
            action="change_account_schema",
            description=(
                f"Changed account schema from '{old_schema}' to '{cleaned_new_schema}', "
                f"tenant name to '{client.name}', and store name to '{final_store_name}'"
            ),
            metadata={
                "client_id": client.id,
                "target_user_id": target_user.id if target_user else None,
                "old_schema": old_schema,
                "new_schema": cleaned_new_schema,
                "old_tenant_name": old_tenant_name,
                "new_tenant_name": client.name,
                "old_store_name": old_store_name,
                "new_store_name": final_store_name,
            },
        )

    tokens = generate_fresh_tokens(target_user) if target_user else None

    return {
        "status": "success",
        "message": "Account database schema name, tenant name, and store name updated successfully.",
        "client_id": client.id,
        "tenant_name": client.name,
        "old_tenant_name": old_tenant_name,
        "new_tenant_name": client.name,
        "old_schema_name": old_schema,
        "new_schema_name": cleaned_new_schema,
        "old_store_name": old_store_name,
        "new_store_name": final_store_name,
        "domains": list(
            Domain.objects.filter(tenant=client).values_list("domain", flat=True)
        ),
        "sub_domain": target_user.sub_domain if target_user else cleaned_new_schema,
        "tokens": tokens,
    }
