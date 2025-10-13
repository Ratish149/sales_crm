from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
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
    """
    POST /api/themes/<id>/publish/
    """

    def post(self, request, id):
        theme = get_object_or_404(Theme, id=id, status="draft")
        publish_instance(theme)
        return Response({"detail": "Theme published successfully"})


# -------------------- PAGE --------------------
class PageListCreateView(generics.ListCreateAPIView):
    serializer_class = PageSerializer

    def get_queryset(self):
        status_param = self.request.query_params.get("status")
        if status_param == "preview":
            return Page.objects.all()
        return Page.objects.filter(status="published")

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

    def perform_update(self, serializer):
        serializer.save(status="draft")


class PagePublishView(APIView):
    """
    POST /api/pages/<slug>/publish/
    """

    @transaction.atomic
    def post(self, request, slug):
        page = get_object_or_404(Page, slug=slug, status="draft")

        # Publish related components first
        for comp in page.components.filter(status="draft"):
            publish_instance(comp)

        # Then publish the page itself
        publish_instance(page)
        return Response({"detail": "Page and its components published successfully"})


# -------------------- NAVBAR --------------------
class NavbarView(generics.GenericAPIView):
    serializer_class = PageComponentSerializer

    def get_object(self):
        status_param = self.request.query_params.get("status")
        if status_param == "preview":
            return PageComponent.objects.filter(component_type="navbar").first()
        return PageComponent.objects.filter(
            component_type="navbar", status="published"
        ).first()

    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        if not obj:
            return Response(
                {"detail": "Navbar not found"}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(self.get_serializer(obj).data)

    def post(self, request, *args, **kwargs):
        if self.get_object():
            return Response(
                {"detail": "Navbar already exists"}, status=status.HTTP_400_BAD_REQUEST
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(component_type="navbar", status="draft")
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def patch(self, request, *args, **kwargs):
        obj = self.get_object()
        if not obj:
            return Response(
                {"detail": "Navbar not found"}, status=status.HTTP_404_NOT_FOUND
            )

        new_data = request.data.get("data", {})
        if new_data and isinstance(new_data, dict):
            current_data = obj.data or {}
            current_data.update(new_data)
            request.data["data"] = current_data

        obj = get_or_create_draft(obj)
        serializer = self.get_serializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(status="draft")
        return Response(serializer.data)

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        if not obj:
            return Response(
                {"detail": "Navbar not found"}, status=status.HTTP_404_NOT_FOUND
            )
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# -------------------- FOOTER --------------------
class FooterView(NavbarView):
    """
    Same logic as Navbar, just for footer
    """

    def get_object(self):
        status_param = self.request.query_params.get("status")
        if status_param == "preview":
            return PageComponent.objects.filter(component_type="footer").first()
        return PageComponent.objects.filter(
            component_type="footer", status="published"
        ).first()


# -------------------- PAGE COMPONENTS --------------------
class PageComponentListCreateView(generics.ListCreateAPIView):
    serializer_class = PageComponentSerializer

    def get_queryset(self):
        slug = self.kwargs["slug"]
        status_param = self.request.query_params.get("status")

        qs = PageComponent.objects.filter(page__slug=slug).exclude(
            component_type__in=["navbar", "footer"]
        )
        if status_param == "preview":
            return qs
        return qs.filter(status="published")

    def perform_create(self, serializer):
        slug = self.kwargs["slug"]
        page = get_object_or_404(Page, slug=slug)
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


class PageComponentPublishView(APIView):
    """
    POST /api/pages/<slug>/components/<component_id>/publish/
    """

    def post(self, request, slug, component_id):
        comp = get_object_or_404(
            PageComponent, page__slug=slug, component_id=component_id, status="draft"
        )
        publish_instance(comp)
        return Response({"detail": "Component published successfully"})


# -------------------- PUBLISH ALL --------------------
class PublishAllView(APIView):
    """
    Publish all draft items at once using proper sync logic.
    URL: /api/publish-all/
    """

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        # Publish components first
        for comp in PageComponent.objects.filter(status="draft"):
            publish_instance(comp)
        # Then pages
        for page in Page.objects.filter(status="draft"):
            publish_instance(page)
        # Then themes
        for theme in Theme.objects.filter(status="draft"):
            publish_instance(theme)

        return Response(
            {"detail": "All drafts published successfully"},
            status=status.HTTP_200_OK,
        )
