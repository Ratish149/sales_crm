# utils.py
import re
from copy import deepcopy

from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import ForeignKey
from django_tenants.utils import schema_context

from collection.models import Collection
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


def update_collection_references(data, collection_map):
    """
    Recursively update collection IDs in a JSON structure.
    """
    if isinstance(data, dict):
        new_data = {}
        for k, v in data.items():
            if k in [
                "collection",
                "collection_id",
                "collectionId",
                "model",
            ] and isinstance(v, int):
                new_data[k] = collection_map.get(v, v)
            else:
                new_data[k] = update_collection_references(v, collection_map)
        return new_data
    elif isinstance(data, list):
        return [update_collection_references(item, collection_map) for item in data]
    else:
        return data


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

        # 1b) IDENTIFY COLLECTIONS TO IMPORT
        # Import all collections from the template account
        source_collections = list(Collection.objects.all())

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
            # Check if an identical collection already exists in target tenant
            existing_coll = Collection.objects.filter(
                name=coll.name, slug=coll.slug, fields=coll.fields
            ).first()

            if existing_coll:
                collection_map[coll.id] = existing_coll.id
                continue

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
                send_email=False,
                admin_email=None,
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


def import_template_to_tenant_published(template_client, target_client):
    """
    Imports a template to a tenant and automatically publishes all the imported drafts,
    replacing the entire published site with the new template.
    """
    # First, import the template (this creates drafts and deletes old drafts)
    import_template_to_tenant(template_client, target_client)

    with schema_context(target_client.schema_name):
        # Delete existing published items to fully replace the site
        PageComponent.objects.filter(status="published").delete()
        Page.objects.filter(status="published").delete()
        Theme.objects.filter(status="published").delete()

        # Publish the newly imported drafts
        for theme in Theme.objects.filter(status="draft"):
            publish_instance(theme)

        for page in Page.objects.filter(status="draft"):
            publish_instance(page)

        for comp in PageComponent.objects.filter(status="draft"):
            publish_instance(comp)

    return True


def import_template_data_to_tenant(template_client, target_client):
    import traceback

    from django.core.files.base import ContentFile
    from django.db import models

    from blog.models import Blog, Tags
    from collection.models import Collection, CollectionData
    from faq.models import FAQ, FAQCategory
    from our_client.models import OurClient
    from portfolio.models import (
        Portfolio,
        PortfolioCategory,
        PortfolioImage,
        PortfolioTags,
    )
    from product.models import (
        Category,
        PricingMetric,
        Product,
        ProductComposition,
        ProductImage,
        ProductOption,
        ProductOptionValue,
        ProductVariant,
        SubCategory,
    )
    from service.models import Service, ServiceCategory
    from team.models import TeamMember
    from testimonial.models import Testimonial
    from videos.models import Video

    def get_unique_fields(model):
        """
        Get all unique constraints from model
        """
        unique_groups = []

        # unique=True fields
        for field in model._meta.fields:
            if field.unique:
                unique_groups.append([field.name])

        # unique_together
        if hasattr(model._meta, "unique_together"):
            for group in model._meta.unique_together:
                unique_groups.append(list(group))

        # UniqueConstraint
        for constraint in model._meta.constraints:
            if isinstance(constraint, models.UniqueConstraint):
                unique_groups.append(list(constraint.fields))

        return unique_groups

    def find_existing_instance(model, data):
        """
        Dynamically find duplicates using model unique constraints
        """

        # slug priority
        if "slug" in data and data["slug"]:
            obj = model.objects.filter(slug=data["slug"]).first()
            if obj:
                return obj

        # name priority
        if "name" in data and data["name"]:
            filters = {"name": data["name"]}

            if "product_id" in data:
                filters["product_id"] = data["product_id"]

            if "category_id" in data:
                filters["category_id"] = data["category_id"]

            if "option_id" in data:
                filters["option_id"] = data["option_id"]

            if "metric_id" in data:
                filters["metric_id"] = data["metric_id"]

            obj = model.objects.filter(**filters).first()
            if obj:
                return obj

        # Dynamic unique constraints
        unique_groups = get_unique_fields(model)

        for fields in unique_groups:
            filters = {}

            for field_name in fields:
                if field_name.endswith("_id"):
                    value = data.get(field_name)

                elif f"{field_name}_id" in data:
                    value = data.get(f"{field_name}_id")

                else:
                    value = data.get(field_name)

                if value is None:
                    filters = None
                    break

                if field_name.endswith("_id"):
                    filters[field_name] = value

                elif f"{field_name}_id" in data:
                    filters[f"{field_name}_id"] = value

                else:
                    filters[field_name] = value

            if filters:
                obj = model.objects.filter(**filters).first()
                if obj:
                    return obj

        return None

    def copy_instances(
        model,
        source_instances,
        fk_maps=None,
        file_fields=None,
        m2m_data=None,
    ):
        print("\n" + "=" * 80)
        print(f"START COPYING: {model.__name__}")
        print("=" * 80)

        id_map = {}
        m2m_updates = []

        for index, src in enumerate(source_instances, start=1):
            try:
                print(
                    f"[{model.__name__}] Processing "
                    f"{index}/{len(source_instances)} "
                    f"(Source ID={src.id})"
                )

                data = {}

                # -----------------------------------
                # Extract fields
                # -----------------------------------
                for field in model._meta.fields:
                    if field.name in [
                        "id",
                        "pk",
                        "created_at",
                        "updated_at",
                    ]:
                        continue

                    # File fields
                    if file_fields and field.name in file_fields:
                        file_obj = getattr(src, field.name)

                        if file_obj and file_obj.name:
                            try:
                                file_obj.open("rb")

                                data[field.name] = ContentFile(
                                    file_obj.read(),
                                    name=file_obj.name.split("/")[-1],
                                )

                            except Exception as e:
                                print(
                                    f"[FILE ERROR] {model.__name__}.{field.name}: {e}"
                                )

                        continue

                    # FK fields
                    if field.is_relation:
                        data[field.attname] = getattr(
                            src,
                            field.attname,
                        )

                    else:
                        data[field.name] = getattr(
                            src,
                            field.name,
                        )

                # -----------------------------------
                # Apply FK mapping
                # -----------------------------------
                skip_record = False

                if fk_maps:
                    for fk_field, mapping in fk_maps.items():
                        key = f"{fk_field}_id"

                        old_fk_id = data.get(key)

                        if old_fk_id:
                            if old_fk_id in mapping:
                                data[key] = mapping[old_fk_id]

                            else:
                                print(
                                    f"[FK NOT FOUND] "
                                    f"{model.__name__}.{fk_field}: "
                                    f"{old_fk_id}"
                                )

                                skip_record = True
                                break

                if skip_record:
                    continue

                # -----------------------------------
                # Duplicate detection
                # -----------------------------------
                existing = find_existing_instance(
                    model,
                    data,
                )

                if existing:
                    print(
                        f"[SKIPPED] {model.__name__} already exists (ID={existing.id})"
                    )

                    id_map[src.id] = existing.id
                    continue

                # -----------------------------------
                # Create
                # -----------------------------------
                print(f"[CREATE] Creating {model.__name__}")

                new_obj = model.objects.create(**data)

                print(f"[SUCCESS] Created {model.__name__} (ID={new_obj.id})")

                id_map[src.id] = new_obj.id

                # -----------------------------------
                # Store m2m
                # -----------------------------------
                if m2m_data:
                    for field_name, m2m_info in m2m_data.items():
                        old_ids = m2m_info["links"].get(
                            src.id,
                            [],
                        )

                        mapping = m2m_info["mapping"]

                        new_ids = [mapping[x] for x in old_ids if x in mapping]

                        if new_ids:
                            m2m_updates.append((
                                new_obj,
                                field_name,
                                new_ids,
                            ))

            except Exception as e:
                print(f"[ERROR] {model.__name__} (Source ID={src.id})")

                print(f"Reason: {str(e)}")

                traceback.print_exc()

        # -----------------------------------
        # Apply m2m
        # -----------------------------------
        for obj, field_name, ids in m2m_updates:
            try:
                getattr(
                    obj,
                    field_name,
                ).set(ids)

                print(f"[M2M SUCCESS] {obj.__class__.__name__}.{field_name}")

            except Exception as e:
                print(f"[M2M ERROR] {obj.__class__.__name__}.{field_name}: {e}")

        print(f"[DONE] {model.__name__}")

        return id_map

    # =====================================
    # FETCH FROM TEMPLATE
    # =====================================
    with schema_context(template_client.schema_name):
        src_categories = list(Category.objects.all())
        src_subcats = list(SubCategory.objects.all())
        src_metrics = list(PricingMetric.objects.all())
        src_products = list(Product.objects.all())
        src_pcomps = list(ProductComposition.objects.all())
        src_pimgs = list(ProductImage.objects.all())
        src_popts = list(ProductOption.objects.all())
        src_poptvals = list(ProductOptionValue.objects.all())
        src_pvariants = list(ProductVariant.objects.all())

        variant_m2m = {
            x.id: list(
                x.option_values.values_list(
                    "id",
                    flat=True,
                )
            )
            for x in src_pvariants
        }

        src_tags = list(Tags.objects.all())
        src_blogs = list(Blog.objects.all())

        blog_m2m = {
            x.id: list(
                x.tags.values_list(
                    "id",
                    flat=True,
                )
            )
            for x in src_blogs
        }

        src_testimonials = list(Testimonial.objects.all())

        src_faqcats = list(FAQCategory.objects.all())
        src_faqs = list(FAQ.objects.all())

        src_team = list(TeamMember.objects.all())

        src_svccats = list(ServiceCategory.objects.all())
        src_svcs = list(Service.objects.all())

        src_portcats = list(PortfolioCategory.objects.all())
        src_porttags = list(PortfolioTags.objects.all())
        src_ports = list(Portfolio.objects.all())
        src_portimgs = list(PortfolioImage.objects.all())

        port_m2m = {
            x.id: list(
                x.tags.values_list(
                    "id",
                    flat=True,
                )
            )
            for x in src_ports
        }

        src_clients = list(OurClient.objects.all())
        src_videos = list(Video.objects.all())

        src_coldata = list(CollectionData.objects.all())
        src_cols = list(Collection.objects.all())

    # =====================================
    # SAVE TO TARGET
    # =====================================
    with schema_context(target_client.schema_name):
        cat_map = copy_instances(
            Category,
            src_categories,
            file_fields=["image"],
        )

        subcat_map = copy_instances(
            SubCategory,
            src_subcats,
            fk_maps={"category": cat_map},
            file_fields=["image"],
        )

        metric_map = copy_instances(
            PricingMetric,
            src_metrics,
        )

        product_map = copy_instances(
            Product,
            src_products,
            fk_maps={
                "category": cat_map,
                "sub_category": subcat_map,
            },
            file_fields=["thumbnail_image"],
        )

        copy_instances(
            ProductComposition,
            src_pcomps,
            fk_maps={
                "product": product_map,
                "metric": metric_map,
            },
        )

        copy_instances(
            ProductImage,
            src_pimgs,
            fk_maps={
                "product": product_map,
            },
            file_fields=["image"],
        )

        popt_map = copy_instances(
            ProductOption,
            src_popts,
            fk_maps={
                "product": product_map,
            },
        )

        poptval_map = copy_instances(
            ProductOptionValue,
            src_poptvals,
            fk_maps={
                "option": popt_map,
            },
        )

        copy_instances(
            ProductVariant,
            src_pvariants,
            fk_maps={
                "product": product_map,
            },
            file_fields=["image"],
            m2m_data={
                "option_values": {
                    "links": variant_m2m,
                    "mapping": poptval_map,
                }
            },
        )

        tag_map = copy_instances(
            Tags,
            src_tags,
        )

        copy_instances(
            Blog,
            src_blogs,
            file_fields=["thumbnail_image"],
            m2m_data={
                "tags": {
                    "links": blog_m2m,
                    "mapping": tag_map,
                }
            },
        )

        copy_instances(
            Testimonial,
            src_testimonials,
            file_fields=["image"],
        )

        faqcat_map = copy_instances(
            FAQCategory,
            src_faqcats,
        )

        copy_instances(
            FAQ,
            src_faqs,
            fk_maps={
                "category": faqcat_map,
            },
        )

        copy_instances(
            TeamMember,
            src_team,
            file_fields=["photo"],
        )

        svccat_map = copy_instances(
            ServiceCategory,
            src_svccats,
            file_fields=["thumbnail_image"],
        )

        copy_instances(
            Service,
            src_svcs,
            fk_maps={
                "service_category": svccat_map,
            },
            file_fields=["thumbnail_image"],
        )

        portcat_map = copy_instances(
            PortfolioCategory,
            src_portcats,
        )

        porttag_map = copy_instances(
            PortfolioTags,
            src_porttags,
        )

        port_map = copy_instances(
            Portfolio,
            src_ports,
            fk_maps={
                "category": portcat_map,
            },
            file_fields=["thumbnail_image"],
            m2m_data={
                "tags": {
                    "links": port_m2m,
                    "mapping": porttag_map,
                }
            },
        )

        copy_instances(
            PortfolioImage,
            src_portimgs,
            fk_maps={
                "portfolio": port_map,
            },
            file_fields=["image"],
        )

        copy_instances(
            OurClient,
            src_clients,
            file_fields=["logo"],
        )

        copy_instances(
            Video,
            src_videos,
        )

        col_map = copy_instances(
            Collection,
            src_cols,
        )

        copy_instances(
            CollectionData,
            src_coldata,
            fk_maps={
                "collection": col_map,
            },
        )

    return True
