from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Page, PageComponent, Theme
from .serializers import PageComponentSerializer, PageSerializer, ThemeSerializer
from .utils import get_or_create_draft, publish_instance


# -------------------- THEME --------------------
class ThemeListCreateView(generics.ListCreateAPIView):
    serializer_class = ThemeSerializer

    def get_queryset(self):
        status_param = self.request.query_params.get("status")
        if status_param == "preview":
            return Theme.objects.all()
        return Theme.objects.filter(status="published")

    def perform_create(self, serializer):
        serializer.save(status="draft")


class ThemeRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ThemeSerializer
    queryset = Theme.objects.all()

    def get_object(self):
        theme = super().get_object()
        edit_mode = self.request.query_params.get("edit")
        if edit_mode and theme.status == "published":
            theme = get_or_create_draft(theme)
        return theme

    def perform_update(self, serializer):
        serializer.save(status="draft")


class ThemePublishView(APIView):
    def post(self, request, id):
        theme = get_object_or_404(Theme, id=id, status="draft")
        publish_instance(theme)
        return Response({"detail": "Theme published successfully"})


# -------------------- PAGE --------------------
class PageListCreateView(generics.ListCreateAPIView):
    serializer_class = PageSerializer

    def get_queryset(self):
        status_param = self.request.query_params.get("status")
        return (
            Page.objects.all()
            if status_param == "preview"
            else Page.objects.filter(status="published")
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["status"] = self.request.query_params.get("status", "live")
        return context

    def perform_create(self, serializer):
        serializer.save(status="draft")


class PageRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PageSerializer
    queryset = Page.objects.all()
    lookup_field = "slug"

    def get_object(self):
        page = super().get_object()
        edit_mode = self.request.query_params.get("edit")
        if edit_mode and page.status == "published":
            page = get_or_create_draft(page)
        return page

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["status"] = self.request.query_params.get("status", "live")
        return context

    def perform_update(self, serializer):
        serializer.save(status="draft")


class PagePublishView(APIView):
    @transaction.atomic
    def post(self, request, slug):
        page = get_object_or_404(Page, slug=slug, status="draft")
        for comp in page.components.filter(status="draft"):
            publish_instance(comp)
        publish_instance(page)
        return Response({"detail": "Page and its components published successfully"})


# -------------------- NAVBAR & FOOTER --------------------
class NavbarView(generics.GenericAPIView):
    serializer_class = PageComponentSerializer
    component_type = "navbar"

    def get_object(self):
        status_param = self.request.query_params.get("status")
        qs = PageComponent.objects.filter(component_type="navbar")
        if status_param == "preview":
            # Show all navbars when preview is requested
            pass
        else:
            # Default behavior: show only published navbars
            qs = qs.filter(status="published")
        return qs.first()

    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        if not obj:
            component_type = getattr(self, "component_type", "navbar")
            return Response(
                {"detail": f"{component_type.title()} not found"}, status=404
            )
        return Response(self.get_serializer(obj).data)

    def post(self, request, *args, **kwargs):
        if self.get_object():
            return Response(
                {"detail": f"{self.component_type.title()} already exists"}, status=400
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(component_type=self.component_type, status="draft")
        return Response(serializer.data, status=201)

    def patch(self, request, *args, **kwargs):
        obj = self.get_object()
        if not obj:
            return Response(
                {"detail": f"{self.component_type.title()} not found"}, status=404
            )
        obj = get_or_create_draft(obj)
        new_data = request.data.get("data", {})
        if new_data:
            current_data = obj.data or {}
            current_data.update(new_data)
            request.data["data"] = current_data
        serializer = self.get_serializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(status="draft")
        return Response(serializer.data)

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj:
            obj.delete()
        return Response(status=204)


class FooterView(NavbarView):
    component_type = "footer"

    def get_object(self):
        status_param = self.request.query_params.get("status")
        qs = PageComponent.objects.filter(component_type="footer")
        if status_param == "preview":
            # Show all footers when preview is requested
            pass
        else:
            # Default behavior: show only published footers
            qs = qs.filter(status="published")
        return qs.first()


# -------------------- PAGE COMPONENTS --------------------
class PageComponentListCreateView(generics.ListCreateAPIView):
    serializer_class = PageComponentSerializer

    def get_queryset(self):
        slug = self.kwargs["slug"]
        status_param = self.request.query_params.get("status")
        qs = PageComponent.objects.filter(page__slug=slug).exclude(
            component_type__in=["navbar", "footer"]
        )
        if status_param != "preview":
            qs = qs.filter(status="published")
        return qs

    def perform_create(self, serializer):
        slug = self.kwargs["slug"]
        page = get_object_or_404(Page, slug=slug)

        # Create new draft always; do not try to merge if duplicates are allowed
        order = serializer.validated_data.get("order", page.components.count())
        serializer.save(page=page, order=order, status="draft")


class PageComponentByTypeView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PageComponentSerializer

    def get_object(self):
        slug = self.kwargs["slug"]
        component_id = self.kwargs["component_id"]
        comp = get_object_or_404(
            PageComponent, page__slug=slug, component_id=component_id
        )
        edit_mode = self.request.query_params.get("edit")
        if edit_mode and comp.status == "published":
            comp = get_or_create_draft(comp)
        return comp

    def perform_update(self, serializer):
        serializer.save(status="draft")

    def patch(self, request, *args, **kwargs):
        obj = self.get_object()
        new_data = request.data.get("data", {})
        if new_data:
            current_data = obj.data or {}
            current_data.update(new_data)
            request.data["data"] = current_data
        return super().patch(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        obj = self.get_object()
        new_data = request.data.get("data", {})
        if new_data:
            current_data = obj.data or {}
            current_data.update(new_data)
            request.data["data"] = current_data
        return super().put(request, *args, **kwargs)


class PageComponentPublishView(APIView):
    def post(self, request, slug, component_id):
        comp = get_object_or_404(
            PageComponent, page__slug=slug, component_id=component_id, status="draft"
        )
        publish_instance(comp)
        return Response({"detail": "Component published successfully"})


# -------------------- PUBLISH ALL --------------------
class PublishAllView(APIView):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        for comp in PageComponent.objects.filter(status="draft"):
            publish_instance(comp)
        for page in Page.objects.filter(status="draft"):
            publish_instance(page)
        for theme in Theme.objects.filter(status="draft"):
            publish_instance(theme)
        return Response({"detail": "All drafts published successfully"}, status=200)
