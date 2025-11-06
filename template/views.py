from django.shortcuts import get_object_or_404
from rest_framework import generics

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
    queryset = TemplatePage.objects.all()

    def perform_create(self, serializer):
        template_id = self.request.data.get("template")
        template = get_object_or_404(Template, id=template_id)
        serializer.save(template=template)


class TemplatePageRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TemplatePageSerializer
    queryset = TemplatePage.objects.all()
    lookup_field = "slug"


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
