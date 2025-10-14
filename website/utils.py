# utils.py
from copy import deepcopy

from django.db import transaction
from django.db.models import ForeignKey


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
    Handles JSONField merging and assigns ForeignKeys to published versions.
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

        # If it's a ForeignKey, link to the published version
        if isinstance(f, ForeignKey) and value:
            if hasattr(value, "published_version") and value.published_version:
                value = value.published_version

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
