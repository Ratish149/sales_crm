import json
from copy import deepcopy

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.db import transaction
from django.shortcuts import get_object_or_404

from tenants.models import Client

from .models import Page, PageComponent, SiteConfig, Theme
from .serializers import (
    PageComponentSerializer,
    PageSerializer,
    SiteConfigSerializer,
    ThemeSerializer,
)
from .utils import import_template_to_tenant, publish_instance


class WebsiteConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.schema_name = self.scope["url_route"]["kwargs"]["schema_name"]
        self.room_group_name = f"website_{self.schema_name}"

        # Add to group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # Leave group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({"error": "Invalid JSON"}))
            return

        action = data.get("action")

        # Switch context to the tenant schema
        await self.set_tenant_context()

        if action == "get_site_config":
            await self.get_site_config()
        elif action == "update_site_config":
            await self.update_site_config(data)
        elif action == "list_themes":
            await self.list_themes(data)
        elif action == "update_theme":
            await self.update_theme(data)
        elif action == "publish_theme":
            await self.publish_theme(data)
        elif action == "list_pages":
            await self.list_pages(data)
        elif action == "create_page":
            await self.create_page(data)
        elif action == "update_page":
            await self.update_page(data)
        elif action == "publish_page":
            await self.publish_page(data)
        elif action == "list_components":
            await self.list_components(data)
        elif action == "create_component":
            await self.create_component(data)
        elif action == "update_component":
            await self.update_component(data)
        elif action == "publish_component":
            await self.publish_component(data)
        elif action == "replace_component":
            await self.replace_component(data)
        elif action == "get_navbar":
            await self.get_navbar(data)
        elif action == "update_navbar":
            await self.update_navbar(data)
        elif action == "publish_navbar":
            await self.publish_navbar(data)
        elif action == "replace_navbar":
            await self.replace_navbar(data)
        elif action == "get_footer":
            await self.get_footer(data)
        elif action == "update_footer":
            await self.update_footer(data)
        elif action == "publish_footer":
            await self.publish_footer(data)
        elif action == "replace_footer":
            await self.replace_footer(data)
        elif action == "publish_all":
            await self.publish_all()
        elif action == "reset_ui":
            await self.reset_ui()
        elif action == "import_template":
            await self.import_template(data)
        else:
            await self.send(
                text_data=json.dumps({"error": f"Unknown action: {action}"})
            )

    @sync_to_async
    def set_tenant_context(self):
        from django.db import connection

        connection.set_schema(self.schema_name)

    # --- Site Config ---
    async def get_site_config(self):
        config = await sync_to_async(
            SiteConfig.objects.get_or_create
        )()  # SiteConfig is Singleton
        serializer = SiteConfigSerializer(config[0])
        await self.send(
            text_data=json.dumps({"action": "site_config", "data": serializer.data})
        )

    async def update_site_config(self, data):
        config = await sync_to_async(SiteConfig.objects.get)()
        serializer = SiteConfigSerializer(config, data=data, partial=True)
        if await sync_to_async(serializer.is_valid)():
            await sync_to_async(serializer.save)()
            await self.send(
                text_data=json.dumps(
                    {"action": "site_config_updated", "data": serializer.data}
                )
            )
        else:
            await self.send(text_data=json.dumps({"error": serializer.errors}))

    # --- Theme ---
    async def list_themes(self, data):
        status_param = data.get("status")
        if status_param == "preview":
            qs = await sync_to_async(list)(Theme.objects.filter(status="draft"))
        else:
            qs = await sync_to_async(list)(Theme.objects.filter(status="published"))
        serializer = ThemeSerializer(qs, many=True)
        await self.send(
            text_data=json.dumps({"action": "themes_list", "data": serializer.data})
        )

    async def update_theme(self, data):
        pk = data.get("id")
        theme = await sync_to_async(get_object_or_404)(Theme, id=pk)
        serializer = ThemeSerializer(theme, data=data, partial=True)
        if await sync_to_async(serializer.is_valid)():
            await sync_to_async(serializer.save)(status="draft")
            await self.send(
                text_data=json.dumps(
                    {"action": "theme_updated", "data": serializer.data}
                )
            )
        else:
            await self.send(text_data=json.dumps({"error": serializer.errors}))

    async def publish_theme(self, data):
        pk = data.get("id")
        theme = await sync_to_async(get_object_or_404)(Theme, id=pk, status="draft")
        await sync_to_async(publish_instance)(theme)
        await self.send(text_data=json.dumps({"action": "theme_published", "id": pk}))

    # --- Page ---
    async def list_pages(self, data):
        status_param = data.get("status")
        if status_param == "preview":
            qs = await sync_to_async(list)(Page.objects.filter(status="draft"))
        else:
            qs = await sync_to_async(list)(Page.objects.filter(status="published"))
        serializer = PageSerializer(qs, many=True)
        await self.send(
            text_data=json.dumps({"action": "pages_list", "data": serializer.data})
        )

    async def create_page(self, data):
        serializer = PageSerializer(data=data)
        if await sync_to_async(serializer.is_valid)():
            await sync_to_async(serializer.save)(status="draft")
            await self.send(
                text_data=json.dumps(
                    {"action": "page_created", "data": serializer.data}
                )
            )
        else:
            await self.send(text_data=json.dumps({"error": serializer.errors}))

    async def update_page(self, data):
        slug = data.get("slug")
        page = await sync_to_async(get_object_or_404)(Page, slug=slug)
        serializer = PageSerializer(page, data=data, partial=True)
        if await sync_to_async(serializer.is_valid)():
            await sync_to_async(serializer.save)(status="draft")
            await self.send(
                text_data=json.dumps(
                    {"action": "page_updated", "data": serializer.data}
                )
            )
        else:
            await self.send(text_data=json.dumps({"error": serializer.errors}))

    @sync_to_async
    def publish_page_sync(self, slug):
        with transaction.atomic():
            page = get_object_or_404(Page, slug=slug, status="draft")
            if page.published_version:
                published_page = page.published_version
                published_components = PageComponent.objects.filter(
                    page=published_page, status="published"
                )
                for comp in published_components:
                    if not PageComponent.objects.filter(
                        published_version=comp
                    ).exists():
                        comp.delete()
            for comp in page.components.filter(status="draft"):
                publish_instance(comp)
            publish_instance(page)
            return page.id

    async def publish_page(self, data):
        slug = data.get("slug")
        page_id = await self.publish_page_sync(slug)
        await self.send(
            text_data=json.dumps(
                {"action": "page_published", "slug": slug, "id": page_id}
            )
        )

    # --- Page Component ---
    async def list_components(self, data):
        slug = data.get("slug")
        status_param = data.get("status", "published")
        page = await sync_to_async(get_object_or_404)(Page, slug=slug)

        if status_param == "preview":
            qs = (
                PageComponent.objects.filter(page=page)
                .exclude(component_type__in=["navbar", "footer"])
                .filter(status="draft")
            )
        elif page.status == "draft" and page.published_version:
            page = page.published_version
            qs = (
                PageComponent.objects.filter(page=page)
                .exclude(component_type__in=["navbar", "footer"])
                .filter(status="published")
            )
        else:
            qs = (
                PageComponent.objects.filter(page=page)
                .exclude(component_type__in=["navbar", "footer"])
                .filter(status="published")
            )

        qs = await sync_to_async(list)(qs.order_by("order"))
        serializer = PageComponentSerializer(qs, many=True)
        await self.send(
            text_data=json.dumps({"action": "components_list", "data": serializer.data})
        )

    async def create_component(self, data):
        slug = data.get("slug")
        page = await sync_to_async(get_object_or_404)(Page, slug=slug)
        serializer = PageComponentSerializer(data=data)
        if await sync_to_async(serializer.is_valid)():
            order = serializer.validated_data.get("order")
            if order is None:
                order = await sync_to_async(page.components.count)()
            await sync_to_async(serializer.save)(page=page, order=order, status="draft")
            await self.send(
                text_data=json.dumps(
                    {"action": "component_created", "data": serializer.data}
                )
            )
        else:
            await self.send(text_data=json.dumps({"error": serializer.errors}))

    async def update_component(self, data):
        slug = data.get("slug")
        component_id = data.get("component_id")
        instance = await sync_to_async(get_object_or_404)(
            PageComponent, page__slug=slug, component_id=component_id
        )
        incoming_data = data.get("data", {})

        def recursive_merge(old, new):
            for key, value in new.items():
                if (
                    key in old
                    and isinstance(old[key], dict)
                    and isinstance(value, dict)
                ):
                    old[key] = recursive_merge(old[key], value)
                else:
                    old[key] = value
            return old

        if instance.data and isinstance(instance.data, dict):
            merged_data = recursive_merge(deepcopy(instance.data), incoming_data)
        else:
            merged_data = incoming_data

        serializer = PageComponentSerializer(
            instance, data={"data": merged_data}, partial=True
        )
        if await sync_to_async(serializer.is_valid)():
            await sync_to_async(serializer.save)(status="draft")
            await self.send(
                text_data=json.dumps(
                    {"action": "component_updated", "data": serializer.data}
                )
            )
        else:
            await self.send(text_data=json.dumps({"error": serializer.errors}))

    @sync_to_async
    def publish_component_sync(self, slug):
        with transaction.atomic():
            component = get_object_or_404(
                PageComponent, page__slug=slug, status="draft"
            )
            for published_component in PageComponent.objects.filter(
                page__slug=slug, status="published"
            ):
                if not PageComponent.objects.filter(
                    published_version=published_component
                ).exists():
                    published_component.delete()
            publish_instance(component)
            return component.id

    async def publish_component(self, data):
        slug = data.get("slug")
        comp_id = await self.publish_component_sync(slug)
        await self.send(
            text_data=json.dumps({"action": "component_published", "id": comp_id})
        )

    @sync_to_async
    def replace_component_sync(self, page_slug, component_id, data):
        with transaction.atomic():
            page = get_object_or_404(Page, slug=page_slug)
            components = PageComponent.objects.filter(
                page=page, component_id=component_id
            )
            if not components.exists():
                return {"error": f"No components found with ID {component_id}"}
            serializer = PageComponentSerializer(data=data)
            if serializer.is_valid():
                orders = list(components.values_list("order", flat=True))
                components.delete()
                created_components = []
                for order in orders:
                    new_component = serializer.save(
                        page=page, order=order, status="draft"
                    )
                    created_components.append(new_component)
                return {
                    "success": True,
                    "data": PageComponentSerializer(created_components, many=True).data,
                }
            return {"error": serializer.errors}

    async def replace_component(self, data):
        page_slug = data.get("page_slug")
        component_id = data.get("component_id")
        # For replacement, we still expect the 'data' field to contain the component structure
        # or we could use the top level as well, but usually replace uses a payload.
        # Let's assume for 'replace' the user sends the new component fields at top level too?
        # Actually replace_component_sync takes 'data'.
        # I'll use 'data' as the fields for the new component.
        result = await self.replace_component_sync(page_slug, component_id, data)
        await self.send(
            text_data=json.dumps({"action": "component_replaced", **result})
        )

    # --- Navbar ---
    async def get_navbar(self, data):
        status_param = data.get("status", "published")
        qs = PageComponent.objects.filter(component_type="navbar")
        if status_param == "preview":
            navbar = await sync_to_async(qs.filter(status="draft").first)()
        else:
            navbar = await sync_to_async(qs.filter(status="published").first)()
        if not navbar:
            await self.send(text_data=json.dumps({"error": "Navbar not found"}))
            return
        await self.send(
            text_data=json.dumps(
                {"action": "navbar", "data": PageComponentSerializer(navbar).data}
            )
        )

    async def update_navbar(self, data):
        pk = data.get("id")
        instance = await sync_to_async(get_object_or_404)(
            PageComponent, id=pk, component_type="navbar"
        )
        incoming_data = data.get("data", data)  # Handles both nested and flat

        def recursive_merge(old, new):
            for key, value in new.items():
                if (
                    key in old
                    and isinstance(old[key], dict)
                    and isinstance(value, dict)
                ):
                    old[key] = recursive_merge(old[key], value)
                else:
                    old[key] = value
            return old

        new_data = incoming_data.get("data", incoming_data)
        if instance.data and isinstance(instance.data, dict):
            merged_data = recursive_merge(deepcopy(instance.data), new_data)
        else:
            merged_data = new_data

        serializer = PageComponentSerializer(
            instance, data={"data": merged_data}, partial=True
        )
        if await sync_to_async(serializer.is_valid)():
            await sync_to_async(serializer.save)(status="draft")
            await self.send(
                text_data=json.dumps(
                    {"action": "navbar_updated", "data": serializer.data}
                )
            )
        else:
            await self.send(text_data=json.dumps({"error": serializer.errors}))

    @sync_to_async
    def publish_navbar_sync(self, pk):
        with transaction.atomic():
            navbar = get_object_or_404(
                PageComponent, id=pk, component_type="navbar", status="draft"
            )
            for published_navbar in PageComponent.objects.filter(
                component_type="navbar", status="published"
            ):
                if not PageComponent.objects.filter(
                    published_version=published_navbar
                ).exists():
                    published_navbar.delete()
            publish_instance(navbar)
            return navbar.id

    async def publish_navbar(self, data):
        pk = data.get("id")
        navbar_id = await self.publish_navbar_sync(pk)
        await self.send(
            text_data=json.dumps({"action": "navbar_published", "id": navbar_id})
        )

    @sync_to_async
    def replace_navbar_sync(self, data):
        with transaction.atomic():
            PageComponent.objects.filter(
                component_type="navbar", status="draft"
            ).delete()
            data["component_type"] = "navbar"
            data["status"] = "draft"
            serializer = PageComponentSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return {"success": True, "data": serializer.data}
            return {"error": serializer.errors}

    async def replace_navbar(self, data):
        result = await self.replace_navbar_sync(data)
        await self.send(text_data=json.dumps({"action": "navbar_replaced", **result}))

    # --- Footer ---
    async def get_footer(self, data):
        status_param = data.get("status", "published")
        qs = PageComponent.objects.filter(component_type="footer")
        if status_param == "preview":
            footer = await sync_to_async(qs.filter(status="draft").first)()
        else:
            footer = await sync_to_async(qs.filter(status="published").first)()
        if not footer:
            await self.send(text_data=json.dumps({"error": "Footer not found"}))
            return
        await self.send(
            text_data=json.dumps(
                {"action": "footer", "data": PageComponentSerializer(footer).data}
            )
        )

    async def update_footer(self, data):
        pk = data.get("id")
        instance = await sync_to_async(get_object_or_404)(
            PageComponent, id=pk, component_type="footer"
        )
        incoming_data = data.get("data", data)

        def recursive_merge(old, new):
            for key, value in new.items():
                if (
                    key in old
                    and isinstance(old[key], dict)
                    and isinstance(value, dict)
                ):
                    old[key] = recursive_merge(old[key], value)
                else:
                    old[key] = value
            return old

        new_data = incoming_data.get("data", incoming_data)
        if instance.data and isinstance(instance.data, dict):
            merged_data = recursive_merge(deepcopy(instance.data), new_data)
        else:
            merged_data = new_data

        serializer = PageComponentSerializer(
            instance, data={"data": merged_data}, partial=True
        )
        if await sync_to_async(serializer.is_valid)():
            await sync_to_async(serializer.save)(status="draft")
            await self.send(
                text_data=json.dumps(
                    {"action": "footer_updated", "data": serializer.data}
                )
            )
        else:
            await self.send(text_data=json.dumps({"error": serializer.errors}))

    @sync_to_async
    def publish_footer_sync(self, pk):
        with transaction.atomic():
            footer = get_object_or_404(
                PageComponent, id=pk, component_type="footer", status="draft"
            )
            for published_footer in PageComponent.objects.filter(
                component_type="footer", status="published"
            ):
                if not PageComponent.objects.filter(
                    published_version=published_footer
                ).exists():
                    published_footer.delete()
            publish_instance(footer)
            return footer.id

    async def publish_footer(self, data):
        pk = data.get("id")
        footer_id = await self.publish_footer_sync(pk)
        await self.send(
            text_data=json.dumps({"action": "footer_published", "id": footer_id})
        )

    @sync_to_async
    def replace_footer_sync(self, data):
        with transaction.atomic():
            PageComponent.objects.filter(
                component_type="footer", status="draft"
            ).delete()
            data["component_type"] = "footer"
            data["status"] = "draft"
            serializer = PageComponentSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return {"success": True, "data": serializer.data}
            return {"error": serializer.errors}

    async def replace_footer(self, data):
        result = await self.replace_footer_sync(data)
        await self.send(text_data=json.dumps({"action": "footer_replaced", **result}))

    # --- Bulk Operations ---
    @sync_to_async
    def publish_all_sync(self):
        with transaction.atomic():
            published_components = PageComponent.objects.filter(status="published")
            published_pages = Page.objects.filter(status="published")
            published_themes = Theme.objects.filter(status="published")

            for comp in published_components:
                if not PageComponent.objects.filter(published_version=comp).exists():
                    comp.delete()
            for page in published_pages:
                if not Page.objects.filter(published_version=page).exists():
                    page.delete()
            for theme in published_themes:
                if not Theme.objects.filter(published_version=theme).exists():
                    theme.delete()

            for theme in Theme.objects.filter(status="draft"):
                publish_instance(theme)
            for page in Page.objects.filter(status="draft"):
                publish_instance(page)
            for comp in PageComponent.objects.filter(status="draft"):
                publish_instance(comp)

    async def publish_all(self):
        await self.publish_all_sync()
        await self.send(text_data=json.dumps({"action": "all_published"}))

    @sync_to_async
    def reset_ui_sync(self):
        with transaction.atomic():
            Theme.objects.filter(status="draft").delete()
            Page.objects.filter(status="draft").delete()
            PageComponent.objects.filter(status="draft").delete()

            theme_map = {}
            for published_theme in Theme.objects.filter(status="published"):
                draft_theme = Theme.objects.create(
                    status="draft",
                    data=deepcopy(published_theme.data),
                    published_version=published_theme,
                )
                theme_map[published_theme.id] = draft_theme

            page_map = {}
            for published_page in Page.objects.filter(status="published"):
                draft_page = Page.objects.create(
                    title=published_page.title,
                    status="draft",
                    theme=theme_map.get(published_page.theme_id),
                    published_version=published_page,
                )
                page_map[published_page.id] = draft_page

            for published_comp in PageComponent.objects.filter(status="published"):
                PageComponent.objects.create(
                    status="draft",
                    page=page_map.get(published_comp.page_id),
                    component_type=published_comp.component_type,
                    component_id=published_comp.component_id,
                    data=deepcopy(published_comp.data),
                    order=published_comp.order,
                    published_version=published_comp,
                )

    async def reset_ui(self):
        await self.reset_ui_sync()
        await self.send(text_data=json.dumps({"action": "ui_reset"}))

    @sync_to_async
    def import_template_sync(self, template_id):
        template_client = Client.objects.get(id=template_id)
        if not template_client.is_template_account:
            return {"error": "Not a template account"}

        # Note: In consumers, we don't have request.tenant like in middleware
        # We assume the schema_name from URL is the correct tenant
        target_client = Client.objects.get(schema_name=self.schema_name)
        import_template_to_tenant(template_client, target_client)
        return {"success": True}

    async def import_template(self, data):
        template_id = data.get("template_id")
        result = await self.import_template_sync(template_id)
        await self.send(text_data=json.dumps({"action": "template_imported", **result}))
