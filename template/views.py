from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Template, TemplatePage, TemplatePageComponent, TemplateTheme
from .serializers import (
    TemplatePageComponentSerializer,
    TemplatePageSerializer,
    TemplateSerializer,
    TemplateThemeSerializer,
)


# ------------------------------
# 🌐 TEMPLATE VIEWS
# ------------------------------
class TemplateListCreateView(generics.ListCreateAPIView):
    serializer_class = TemplateSerializer
    queryset = Template.objects.all()


class TemplateRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TemplateSerializer
    queryset = Template.objects.all()
    lookup_field = "slug"


class TemplateThemeListCreateView(generics.ListCreateAPIView):
    serializer_class = TemplateThemeSerializer
    queryset = TemplateTheme.objects.all()

    def get_queryset(self):
        template_slug = self.kwargs.get("template_slug")
        template = get_object_or_404(Template, slug=template_slug)
        return TemplateTheme.objects.filter(template=template).order_by("id")

    def perform_create(self, serializer):
        template_slug = self.kwargs.get("template_slug")
        template = get_object_or_404(Template, slug=template_slug)
        serializer.save(template=template)


class TemplateThemeRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TemplateThemeSerializer
    queryset = TemplateTheme.objects.all()

    def get_object(self):
        template_slug = self.kwargs.get("template_slug")
        theme_slug = self.kwargs.get("theme_slug")
        return get_object_or_404(
            TemplateTheme, template__slug=template_slug, slug=theme_slug
        )


# ------------------------------
# 📄 TEMPLATE PAGE VIEWS
# ------------------------------
class TemplatePageListCreateView(generics.ListCreateAPIView):
    serializer_class = TemplatePageSerializer

    def get_queryset(self):
        template_slug = self.request.query_params.get("template_slug")
        template = get_object_or_404(Template, slug=template_slug)
        return TemplatePage.objects.filter(template=template).order_by("id")

    def perform_create(self, serializer):
        template_slug = self.request.data.get("template_slug")
        template = get_object_or_404(Template, slug=template_slug)
        serializer.save(template=template)


class TemplatePageRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TemplatePageSerializer
    queryset = TemplatePage.objects.all()

    def get_object(self):
        template_slug = self.kwargs.get("template_slug")
        page_slug = self.kwargs.get("page_slug")
        return get_object_or_404(
            TemplatePage, template__slug=template_slug, slug=page_slug
        )


# ------------------------------
# 🧩 TEMPLATE PAGE COMPONENT VIEWS
# ------------------------------
class TemplatePageComponentListCreateView(generics.ListCreateAPIView):
    serializer_class = TemplatePageComponentSerializer

    def get_queryset(self):
        template_slug = self.kwargs.get("template_slug")
        page_slug = self.kwargs.get("page_slug")
        page = get_object_or_404(
            TemplatePage, template__slug=template_slug, slug=page_slug
        )
        return TemplatePageComponent.objects.filter(page=page).order_by("order")

    def perform_create(self, serializer):
        template_slug = self.kwargs.get("template_slug")
        page_slug = self.kwargs.get("page_slug")
        page = get_object_or_404(
            TemplatePage, template__slug=template_slug, slug=page_slug
        )

        order = serializer.validated_data.get("order")
        if order is None:
            order = page.components.count()

        serializer.save(page=page, order=order)


class TemplatePageComponentRetrieveUpdateDestroyView(
    generics.RetrieveUpdateDestroyAPIView
):
    serializer_class = TemplatePageComponentSerializer

    def get_object(self):
        template_slug = self.kwargs.get("template_slug")
        page_slug = self.kwargs.get("page_slug")
        component_id = self.kwargs.get("component_id")
        page = get_object_or_404(
            TemplatePage, template__slug=template_slug, slug=page_slug
        )
        return get_object_or_404(
            TemplatePageComponent, page=page, component_id=component_id
        )

    def perform_update(self, serializer):
        instance = self.get_object()
        incoming_data = self.request.data.get("data", {})

        def recursive_merge(old, new):
            """
            Recursively merge new dict into old dict
            """
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
            merged_data = recursive_merge(instance.data, incoming_data)
        else:
            merged_data = incoming_data

        serializer.save(data=merged_data)


class NavbarView(APIView):
    def get(self, request, template_slug):
        # Get the template first
        template = get_object_or_404(Template, slug=template_slug)

        # Get the navbar component for this template
        navbar = TemplatePageComponent.objects.filter(
            template=template, component_type="navbar"
        ).first()

        if not navbar:
            return Response(
                {"detail": "Navbar not found for this template"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(TemplatePageComponentSerializer(navbar).data)

    def post(self, request, template_slug):
        # Get the template
        template = get_object_or_404(Template, slug=template_slug)

        # Get the first page for this template (or handle multiple pages appropriately)
        page = TemplatePage.objects.filter(template=template).first()

        if not page:
            return Response(
                {"detail": "No pages found for this template"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check if navbar already exists for this template
        navbar = TemplatePageComponent.objects.filter(
            template=template, component_type="navbar"
        ).first()

        data = request.data.copy()
        data["page"] = page.id
        data["template"] = template.id
        data["component_type"] = "navbar"

        if navbar:
            # Update existing navbar
            serializer = TemplatePageComponentSerializer(
                navbar, data=data, partial=True
            )
        else:
            # Create new navbar
            serializer = TemplatePageComponentSerializer(data=data)

        if serializer.is_valid():
            instance = serializer.save()
            # Ensure template is set on the instance
            if not instance.template:
                instance.template = template
                instance.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class NavbarRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    Edit or delete navbar by ID.
    PATCH /api/navbar/<id>/  → update draft navbar
    """

    serializer_class = TemplatePageComponentSerializer
    queryset = TemplatePageComponent.objects.all()

    def get_object(self):
        template_slug = self.kwargs.get("template_slug")
        pk = self.kwargs.get("pk")
        return TemplatePageComponent.objects.get(template__slug=template_slug, id=pk)

    def perform_update(self, serializer):
        instance = self.get_object()
        incoming_data = self.request.data
        template_slug = self.kwargs.get("template_slug")
        template = get_object_or_404(Template, slug=template_slug)
        page = get_object_or_404(TemplatePage, template=template)
        instance.page = page
        instance.component_type = "navbar"

        # Ensure dict
        if not isinstance(incoming_data, dict):
            incoming_data = {}

        # Recursive merge utility
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

        # If client sends full object with a "data" key, use only that
        new_data = incoming_data.get("data", incoming_data)

        if instance.data and isinstance(instance.data, dict):
            merged_data = recursive_merge(instance.data, new_data)
        else:
            merged_data = new_data

        serializer.save(data=merged_data)


# ------------------------------
# 🦶 FOOTER VIEWS
# ------------------------------
class FooterView(APIView):
    def get(self, request, *args, **kwargs):
        template_slug = self.kwargs.get("template_slug")
        # Get the template first
        template = get_object_or_404(Template, slug=template_slug)

        # Get the footer component for this template
        footer = TemplatePageComponent.objects.filter(
            template=template, component_type="footer"
        ).first()

        if not footer:
            return Response(
                {"detail": "Footer not found for this template"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(TemplatePageComponentSerializer(footer).data)

    def post(self, request, *args, **kwargs):
        template_slug = self.kwargs.get("template_slug")
        # Get the template
        template = get_object_or_404(Template, slug=template_slug)

        # Get the first page for this template (or handle multiple pages appropriately)
        page = TemplatePage.objects.filter(template=template).first()

        if not page:
            return Response(
                {"detail": "No pages found for this template"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check if footer already exists for this template
        footer = TemplatePageComponent.objects.filter(
            template=template, component_type="footer"
        ).first()

        data = request.data.copy()
        data["page"] = page.id
        data["template"] = template.id
        data["component_type"] = "footer"

        if footer:
            # Update existing footer
            serializer = TemplatePageComponentSerializer(
                footer, data=data, partial=True
            )
        else:
            # Create new footer
            serializer = TemplatePageComponentSerializer(data=data)

        if serializer.is_valid():
            instance = serializer.save()
            # Ensure template is set on the instance
            if not instance.template:
                instance.template = template
                instance.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FooterRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TemplatePageComponentSerializer
    queryset = TemplatePageComponent.objects.all()

    def get_object(self):
        template_slug = self.kwargs.get("template_slug")
        pk = self.kwargs.get("pk")
        try:
            return TemplatePageComponent.objects.get(
                template__slug=template_slug,
                id=pk,
                component_type="footer",
            )
        except TemplatePageComponent.DoesNotExist:
            raise Response(
                {"detail": "Footer not found with the given component ID"},
                status=status.HTTP_404_NOT_FOUND,
            )

    def perform_update(self, serializer):
        instance = self.get_object()
        incoming_data = self.request.data
        template_slug = self.kwargs.get("template_slug")
        template = get_object_or_404(Template, slug=template_slug)
        page = get_object_or_404(TemplatePage, template=template)
        instance.page = page
        instance.component_type = "footer"

        # Ensure dict
        if not isinstance(incoming_data, dict):
            incoming_data = {}

        # Recursive merge utility
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

        # If client sends full object with a "data" key, use only that
        new_data = incoming_data.get("data", incoming_data)

        if instance.data and isinstance(instance.data, dict):
            merged_data = recursive_merge(instance.data, new_data)
        else:
            merged_data = new_data

        serializer.save(data=merged_data)
