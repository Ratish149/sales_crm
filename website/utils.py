from django.db import transaction
from django.forms.models import model_to_dict


def get_or_create_draft(instance):
    """
    If the instance is published, return an existing draft or create one.
    """
    if instance.status == "draft":
        return instance

    # If already has draft version, return it
    existing_draft = instance.draft_version.first()
    if existing_draft:
        return existing_draft

    # Otherwise, clone it
    data = model_to_dict(
        instance, exclude=["id", "created_at", "updated_at", "published_version"]
    )
    draft = instance.__class__.objects.create(
        **data, status="draft", published_version=instance
    )
    return draft


@transaction.atomic
def publish_instance(draft_instance):
    """
    Publish the given draft instance: copy its data into the linked published version.
    """
    if draft_instance.status != "draft":
        raise ValueError("Only draft instances can be published.")

    published = draft_instance.published_version

    # If no published version exists, create one
    if not published:
        published = draft_instance.__class__.objects.create(status="published")
        draft_instance.published_version = published
        draft_instance.save()

    # Copy all relevant fields
    data = model_to_dict(
        draft_instance,
        exclude=["id", "created_at", "updated_at", "published_version", "status"],
    )
    for key, value in data.items():
        setattr(published, key, value)
    published.status = "published"
    published.save()

    return published
