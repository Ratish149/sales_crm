# utils.py
import re
from copy import deepcopy

from django.db import transaction
from django.db.models import ForeignKey


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
