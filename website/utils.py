# utils.py
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
        if f.name not in ["id", "created_at", "updated_at", "published_version", "status"]
    }
    draft = model.objects.create(**data, status="draft", published_version=instance)
    return draft


@transaction.atomic
def publish_instance(instance):
    """
    Creates or updates a published version of the given draft.
    """
    if instance.status != "draft":
        return instance

    model = instance.__class__
    data = {
        f.name: getattr(instance, f.name)
        for f in model._meta.fields
        if f.name not in ["id", "created_at", "updated_at", "published_version", "status"]
    }
    data["status"] = "published"

    if instance.published_version:
        # Update the linked published object
        published = instance.published_version
        for key, value in data.items():
            setattr(published, key, value)
        published.save()
    else:
        # Create a new published version
        published = model.objects.create(**data)
        instance.published_version = published
        instance.save(update_fields=["published_version"])

    return published
