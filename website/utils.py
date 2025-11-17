# utils.py
import re
from copy import deepcopy

from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import ForeignKey
from django_tenants.utils import schema_context

from website.models import Page, PageComponent, Theme


def clean_draft_links(data):
    """
    Recursively clean href values containing '-draft' in a dict or list.
    """
    if isinstance(data, dict):
        cleaned = {}
        for key, value in data.items():
            # If it's a dict or list, clean recursively
            if isinstance(value, (dict, list)):
                cleaned[key] = clean_draft_links(value)
            # If it's a string containing href or '-draft'
            elif isinstance(value, str):
                # Remove '-draft' only inside URLs or href-like values
                if (
                    "href" in key.lower()
                    or "url" in key.lower()
                    or "link" in key.lower()
                    or "page-draft" in value
                ):
                    cleaned[key] = re.sub(r"-draft", "", value)
                else:
                    cleaned[key] = value
            else:
                cleaned[key] = value
        return cleaned

    elif isinstance(data, list):
        return [clean_draft_links(item) for item in data]

    else:
        return data


def get_or_create_draft(instance):
    """
    Returns or creates a draft version of a published instance.
    """
    if instance.status == "draft":
        return instance

    model = instance.__class__
    draft = model.objects.filter(published_version=instance).first()
    if draft:
        return draft

    # Create a clone as a new draft
    data = {
        f.name: getattr(instance, f.name)
        for f in model._meta.fields
        if f.name
        not in ["id", "created_at", "updated_at", "published_version", "status"]
    }
    draft = model.objects.create(**data, status="draft", published_version=instance)
    return draft


@transaction.atomic
def publish_instance(instance):
    """
    Publishes a draft instance.
    Handles JSONField merging, cleans draft href links,
    and assigns ForeignKeys to published versions.
    """
    if instance.status != "draft":
        return instance

    model = instance.__class__

    # Collect field data
    data = {}
    for f in model._meta.fields:
        if f.name in ["id", "created_at", "updated_at", "published_version", "status"]:
            continue

        value = getattr(instance, f.name)

        # Handle ForeignKeys: point to published version if exists
        if isinstance(f, ForeignKey) and value:
            if hasattr(value, "published_version") and value.published_version:
                value = value.published_version

        # Clean JSON data for published version (but keep original in draft)
        if f.name == "data" and isinstance(value, dict):
            value = clean_draft_links(deepcopy(value))

        data[f.name] = value

    data["status"] = "published"

    if instance.published_version:
        # Update existing published version
        published = instance.published_version
        for key, value in data.items():
            if key == "data" and isinstance(value, dict):
                old_data = deepcopy(getattr(published, "data") or {})
                old_data.update(value)
                setattr(published, "data", old_data)
            else:
                setattr(published, key, value)
        published.save()
    else:
        # Create new published instance
        published = model.objects.create(**data)
        instance.published_version = published
        instance.save(update_fields=["published_version"])

    return published


def clone_file(field):
    """
    Clone a FileField file so a new tenant has its own file.
    """
    if not field:
        return None

    file_content = field.read()
    filename = field.name.split("/")[-1]
    return ContentFile(file_content, name=filename)


def import_template_to_tenant(template_client, target_client):
    # 1) READ TEMPLATE DATA
    with schema_context(template_client.schema_name):
        source_themes = Theme.objects.filter(status="published")
        source_pages = Page.objects.filter(status="published")
        source_components = PageComponent.objects.filter(status="published")

    # 2) WRITE INTO USER SCHEMA
    with schema_context(target_client.schema_name):
        # ---- DELETE OLD USER DATA ----
        PageComponent.objects.all().delete()
        Page.objects.all().delete()
        Theme.objects.all().delete()

        # ---- COPY THEMES AS DRAFT ----
        theme_map = {}
        for theme in source_themes:
            new_theme = Theme.objects.create(
                status="draft", data=theme.data, published_version=None
            )
            theme_map[theme.id] = new_theme

        # ---- COPY PAGES AS DRAFT ----
        page_map = {}
        for page in source_pages:
            new_page = Page.objects.create(
                title=page.title,
                status="draft",
                theme=theme_map.get(page.theme_id),
                published_version=None,
            )
            page_map[page.id] = new_page

        # ---- COPY COMPONENTS AS DRAFT ----
        for comp in source_components:
            PageComponent.objects.create(
                status="draft",
                page=page_map.get(comp.page_id),
                component_type=comp.component_type,
                component_id=comp.component_id,
                data=comp.data,
                order=comp.order,
                published_version=None,
            )

    return True
