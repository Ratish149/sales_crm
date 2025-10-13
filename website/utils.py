def get_or_create_draft(instance):
    """
    Returns a draft version of the instance.
    If instance is already a draft, returns it.
    If multiple drafts exist, returns the first one.
    """
    if instance.status == "draft":
        return instance

    # Return first draft if it exists
    drafts = instance.draft_version.all() if hasattr(instance, "draft_version") else []
    if drafts:
        return drafts.first()

    # Otherwise, create a new draft copy
    clone = instance.__class__.objects.create(
        **{
            field.name: getattr(instance, field.name)
            for field in instance._meta.fields
            if field.name
            not in ["id", "created_at", "updated_at", "published_version", "status"]
        }
    )
    clone.status = "draft"
    clone.published_version = instance
    clone.save()
    return clone


def publish_instance(instance):
    """
    Publishes a draft instance.
    If the instance has a published_version, it updates it.
    """
    if instance.status != "draft":
        return instance
    published = instance.published_version
    if published:
        # update the published version
        for field in instance._meta.fields:
            if field.name not in [
                "id",
                "created_at",
                "updated_at",
                "published_version",
                "status",
            ]:
                setattr(published, field.name, getattr(instance, field.name))
        published.save()
    else:
        # make this instance published
        instance.status = "published"
        instance.save()
    # Link draft to published
    instance.published_version = published or instance
    instance.save()
    return instance
