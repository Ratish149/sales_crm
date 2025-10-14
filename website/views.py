# views.py
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Page, PageComponent, Theme
from .serializers import PageComponentSerializer, PageSerializer, ThemeSerializer
from .utils import publish_instance


# ------------------------------
# 🌈 THEME VIEWS
# ------------------------------
class ThemeListCreateView(generics.ListCreateAPIView):
    serializer_class = ThemeSerializer
    queryset = Theme.objects.all()

    def get_queryset(self):
        status = self.request.query_params.get("status")
        if status == "preview":
            return Theme.objects.filter(status="draft")
        return Theme.objects.filter(status="published")

    def perform_create(self, serializer):
        serializer.save(status="draft")


class ThemeRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ThemeSerializer
    queryset = Theme.objects.all()

    def perform_update(self, serializer):
        serializer.save(status="draft")


class ThemePublishView(APIView):
    def post(self, request, pk):
        theme = get_object_or_404(Theme, id=pk, status="draft")
        publish_instance(theme)
        return Response({"detail": "Theme published successfully"})


# ------------------------------
# 📄 PAGE VIEWS
# ------------------------------
class PageListCreateView(generics.ListCreateAPIView):
    serializer_class = PageSerializer
    queryset = Page.objects.all()

    def get_queryset(self):
        status = self.request.query_params.get("status")
        if status == "preview":
            return Page.objects.filter(status="draft")
        return Page.objects.filter(status="published")

    def perform_create(self, serializer):
        serializer.save(status="draft")


class PageRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PageSerializer
    queryset = Page.objects.all()
    lookup_field = "slug"

    def perform_update(self, serializer):
        serializer.save(status="draft")


class PagePublishView(APIView):
    @transaction.atomic
    def post(self, request, slug):
        page = get_object_or_404(Page, slug=slug, status="draft")
        # Publish all draft components linked to this page
        for comp in page.components.filter(status="draft"):
            publish_instance(comp)
        publish_instance(page)
        return Response({"detail": "Page and its components published successfully"})


# ------------------------------
# 🧩 PAGE COMPONENT VIEWS
# ------------------------------
class PageComponentListCreateView(generics.ListCreateAPIView):
    serializer_class = PageComponentSerializer

    def get_queryset(self):
        slug = self.kwargs["slug"]
        page = get_object_or_404(Page, slug=slug)
        status = self.request.query_params.get("status")

        qs = PageComponent.objects.filter(page=page).exclude(
            component_type__in=["navbar", "footer"]
        )

        if status == "preview":
            # return only drafts
            return qs.filter(status="draft").order_by("order")
        return qs.filter(status="published").order_by("order")

    def perform_create(self, serializer):
        slug = self.kwargs["slug"]
        page = get_object_or_404(Page, slug=slug)
        order = serializer.validated_data.get("order", page.components.count())
        serializer.save(page=page, order=order, status="draft")


class PageComponentRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PageComponentSerializer
    queryset = PageComponent.objects.all()
    lookup_field = "id"

    def perform_update(self, serializer):
        serializer.save(status="draft")


class PageComponentPublishView(APIView):
    def post(self, request, id):
        component = get_object_or_404(PageComponent, id=id, status="draft")
        publish_instance(component)
        return Response({"detail": "Component published successfully"})


# ------------------------------
# 🧭 NAVBAR VIEWS
# ------------------------------


class NavbarView(APIView):
    """
    GET:
      /api/navbar/                 → published navbar
      /api/navbar?status=preview   → draft navbar
    """

    def get(self, request):
        status_param = request.query_params.get("status", "live")

        qs = PageComponent.objects.filter(component_type="navbar")

        if status_param == "preview":
            navbar = qs.filter(status="draft").first()
        else:
            navbar = qs.filter(status="published").first()

        if not navbar:
            return Response(
                {"detail": "Navbar not found"}, status=status.HTTP_404_NOT_FOUND
            )

        return Response(PageComponentSerializer(navbar).data)


class NavbarRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    Edit or delete navbar by ID.
    PATCH /api/navbar/<id>/  → update draft navbar
    """

    serializer_class = PageComponentSerializer
    queryset = PageComponent.objects.filter(component_type="navbar")

    def perform_update(self, serializer):
        serializer.save(status="draft")


class NavbarPublishView(APIView):
    """
    POST /api/navbar/<id>/publish/
    Publishes the navbar draft.
    """

    def post(self, request, id):
        navbar = get_object_or_404(
            PageComponent, id=id, component_type="navbar", status="draft"
        )
        publish_instance(navbar)
        return Response({"detail": "Navbar published successfully"})


# ------------------------------
# 🦶 FOOTER VIEWS
# ------------------------------
class FooterView(APIView):
    """
    GET:
      /api/footer/                → published footer
      /api/footer?status=preview  → draft footer
    """

    def get(self, request):
        status_param = request.query_params.get("status", "live")

        qs = PageComponent.objects.filter(component_type="footer")

        if status_param == "preview":
            footer = qs.filter(status="draft").first()
        else:
            footer = qs.filter(status="published").first()

        if not footer:
            return Response(
                {"detail": "Footer not found"}, status=status.HTTP_404_NOT_FOUND
            )

        return Response(PageComponentSerializer(footer).data)


class FooterRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    Edit or delete footer by ID.
    PATCH /api/footer/<id>/  → update draft footer
    """

    serializer_class = PageComponentSerializer
    queryset = PageComponent.objects.filter(component_type="footer")

    def perform_update(self, serializer):
        serializer.save(status="draft")


class FooterPublishView(APIView):
    """
    POST /api/footer/<id>/publish/
    Publishes the footer draft.
    """

    def post(self, request, id):
        footer = get_object_or_404(
            PageComponent, id=id, component_type="footer", status="draft"
        )
        publish_instance(footer)
        return Response({"detail": "Footer published successfully"})


# ------------------------------
# 🚀 PUBLISH ALL
# ------------------------------
class PublishAllView(APIView):
    @transaction.atomic
    def post(self, request):
        for comp in PageComponent.objects.filter(status="draft"):
            publish_instance(comp)
        for page in Page.objects.filter(status="draft"):
            publish_instance(page)
        for theme in Theme.objects.filter(status="draft"):
            publish_instance(theme)
        return Response({"detail": "All drafts published successfully"})
