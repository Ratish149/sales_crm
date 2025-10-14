# utils.py
from copy import deepcopy

from django.db import transaction


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
    Creates or updates a published version of the given draft.
    Ensures JSONFields are merged (not overwritten).
    """
    if instance.status != "draft":
        return instance

    model = instance.__class__

    # Collect field data to copy
    data = {
        f.name: getattr(instance, f.name)
        for f in model._meta.fields
        if f.name
        not in ["id", "created_at", "updated_at", "published_version", "status"]
    }
    data["status"] = "published"

    # Get existing published version if it exists
    if instance.published_version:
        published = instance.published_version

        for key, value in data.items():
            if key == "data" and isinstance(value, dict):
                # Deep merge JSON data
                old_data = deepcopy(getattr(published, "data") or {})
                new_data = deepcopy(value)

                # merge (override existing keys, add new ones)
                old_data.update(new_data)

                setattr(published, "data", old_data)
            else:
                setattr(published, key, value)

        published.save()
    else:
        # Create new published copy
        published = model.objects.create(**data)
        instance.published_version = published
        instance.save(update_fields=["published_version"])

    return published
