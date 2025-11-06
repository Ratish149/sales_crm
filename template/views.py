from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Template, TemplatePage, TemplatePageComponent
from .serializers import (
    TemplatePageComponentSerializer,
    TemplatePageSerializer,
    TemplateSerializer,
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


# ------------------------------
# 📄 TEMPLATE PAGE VIEWS
# ------------------------------
class TemplatePageListCreateView(generics.ListCreateAPIView):
    serializer_class = TemplatePageSerializer

    def get_queryset(self):
        template_slug = self.kwargs.get("template_slug")
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
        return get_object_or_404(TemplatePageComponent, page=page, id=component_id)


class NavbarView(APIView):
    def get(self, request):
        template_slug = self.kwargs.get("template_slug")
        navbar = TemplatePageComponent.objects.filter(
            template__slug=template_slug, component_type="navbar"
        ).first()

        if not navbar:
            return Response(
                {"detail": "Navbar not found"}, status=status.HTTP_404_NOT_FOUND
            )

        return Response(TemplatePageComponentSerializer(navbar).data)

    def post(self, request):
        # Always create a draft when posting
        data = request.data.copy()
        data["component_type"] = "navbar"

        serializer = TemplatePageComponentSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
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
        component_id = self.kwargs.get("component_id")
        return TemplatePageComponent.objects.get(
            template__slug=template_slug, id=component_id
        )

    def perform_update(self, serializer):
        instance = self.get_object()
        incoming_data = self.request.data

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
    def get(self, request):
        template_slug = self.kwargs.get("template_slug")
        footer = TemplatePageComponent.objects.filter(
            template__slug=template_slug, component_type="footer"
        )

        if not footer:
            return Response(
                {"detail": "Footer not found"}, status=status.HTTP_404_NOT_FOUND
            )

        return Response(TemplatePageComponentSerializer(footer).data)

    def post(self, request):
        # Always create a draft when posting
        data = request.data.copy()
        data["component_type"] = "footer"

        serializer = TemplatePageComponentSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FooterRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TemplatePageComponentSerializer

    def get_object(self):
        template_slug = self.kwargs.get("template_slug")
        component_id = self.kwargs.get("component_id")
        return TemplatePageComponent.objects.get(
            template__slug=template_slug, id=component_id
        )

    def perform_update(self, serializer):
        instance = self.get_object()
        incoming_data = self.request.data

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
