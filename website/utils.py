# utils.py
import re
from copy import deepcopy

from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import ForeignKey
from django_tenants.utils import schema_context

from website.models import Page, PageComponent, Theme
from collection.models import Collection


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


def update_collection_references(data, collection_map):
    """
    Recursively update collection IDs in a JSON structure.
    """
    if isinstance(data, dict):
        new_data = {}
        for k, v in data.items():
            if k in ["collection", "collection_id", "collectionId", "model"] and isinstance(v, int):
                new_data[k] = collection_map.get(v, v)
            else:
                new_data[k] = update_collection_references(v, collection_map)
        return new_data
    elif isinstance(data, list):
        return [update_collection_references(item, collection_map) for item in data]
    else:
        return data


def find_used_collection_ids(data, found_ids=None):
    """
    Recursively find all collection IDs referenced in a JSON structure.
    """
    if found_ids is None:
        found_ids = set()

    if isinstance(data, dict):
        for k, v in data.items():
            if k in ["collection", "collection_id", "collectionId", "model"] and isinstance(v, int):
                found_ids.add(v)
            else:
                find_used_collection_ids(v, found_ids)
    elif isinstance(data, list):
        for item in data:
            find_used_collection_ids(item, found_ids)

    return found_ids


def import_template_to_tenant(template_client, target_client):
    # 1) READ TEMPLATE DATA
    with schema_context(template_client.schema_name):
        source_themes = list(Theme.objects.filter(status="published"))
        source_pages = list(Page.objects.filter(status="published"))
        source_components = list(PageComponent.objects.filter(status="published"))

        # Navbars & Footers (site-wide)
        source_navbars = [c for c in source_components if c.component_type == "navbar"]
        source_footers = [c for c in source_components if c.component_type == "footer"]
        source_other_components = [
            c for c in source_components if c.component_type not in ["navbar", "footer"]
        ]

        # 1b) IDENTIFY USED COLLECTIONS
        all_collections = {c.id: c for c in Collection.objects.all()}
        used_ids = set()

        # Check themes
        for theme in source_themes:
            find_used_collection_ids(theme.data, used_ids)

        # Check components
        for comp in source_components:
            find_used_collection_ids(comp.data, used_ids)

        # Recursively find dependent collections (collection fields that refer to other collections)
        to_process = list(used_ids)
        while to_process:
            current_id = to_process.pop()
            if current_id in all_collections:
                coll = all_collections[current_id]
                # Check fields for 'model' references
                dep_ids = find_used_collection_ids(coll.fields)
                for d_id in dep_ids:
                    if d_id not in used_ids:
                        used_ids.add(d_id)
                        to_process.append(d_id)

        source_collections = [all_collections[cid] for cid in used_ids if cid in all_collections]

    # 2) WRITE INTO USER SCHEMA
    with schema_context(target_client.schema_name):
        # Delete old data (pages, themes, components - draft only)
        # Note: We do NOT delete existing collections as per user request
        PageComponent.objects.filter(status="draft").delete()
        Page.objects.filter(status="draft").delete()
        Theme.objects.filter(status="draft").delete()

        # Copy collections
        collection_map = {}
        for coll in source_collections:
            unique_name = coll.name
            unique_slug = coll.slug
            
            # Resolve name/slug collisions
            counter = 1
            while Collection.objects.filter(name=unique_name).exists():
                unique_name = f"{coll.name} (Imported {counter})"
                counter += 1
            
            counter = 1
            while Collection.objects.filter(slug=unique_slug).exists():
                unique_slug = f"{coll.slug}-imported-{counter}"
                counter += 1

            new_coll = Collection.objects.create(
                name=unique_name,
                slug=unique_slug,
                send_email=coll.send_email,
                admin_email=coll.admin_email,
                default_fields=coll.default_fields,
                fields=coll.fields,
            )
            collection_map[coll.id] = new_coll.id

        # Update self-references in collection fields (e.g., model references)
        for coll_id in collection_map.values():
            coll = Collection.objects.get(id=coll_id)
            coll.fields = update_collection_references(coll.fields, collection_map)
            coll.save(update_fields=["fields"])

        # Copy themes
        theme_map = {}
        for theme in source_themes:
            # Update data with new collection references
            new_data = update_collection_references(theme.data, collection_map)
            new_theme = Theme.objects.create(
                status="draft", data=new_data, published_version=None
            )
            theme_map[theme.id] = new_theme

        # Copy pages
        page_map = {}
        for page in source_pages:
            new_theme = theme_map.get(page.theme_id)
            new_page = Page.objects.create(
                title=page.title,
                status="draft",
                theme=new_theme,
                published_version=None,
            )
            page_map[page.id] = new_page

        # Copy other components (linked to pages)
        for comp in source_other_components:
            new_page = page_map.get(comp.page_id)
            new_data = update_collection_references(comp.data, collection_map)
            PageComponent.objects.create(
                status="draft",
                page=new_page,
                component_type=comp.component_type,
                component_id=comp.component_id,
                data=new_data,
                order=comp.order,
                published_version=None,
            )

        # Copy navbar/footer (page=None)
        for nav in source_navbars:
            new_data = update_collection_references(nav.data, collection_map)
            PageComponent.objects.create(
                status="draft",
                page=None,
                component_type="navbar",
                component_id=nav.component_id,
                data=new_data,
                order=nav.order,
                published_version=None,
            )

        for foot in source_footers:
            new_data = update_collection_references(foot.data, collection_map)
            PageComponent.objects.create(
                status="draft",
                page=None,
                component_type="footer",
                component_id=foot.component_id,
                data=new_data,
                order=foot.order,
                published_version=None,
            )

    return True
