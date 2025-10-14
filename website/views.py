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
    lookup_field = "id"

    def perform_update(self, serializer):
        serializer.save(status="draft")


class PagePublishView(APIView):
    @transaction.atomic
    def post(self, request, id):
        page = get_object_or_404(Page, id=id, status="draft")
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
        id = self.kwargs["id"]
        page = get_object_or_404(Page, id=id)
        status = self.request.query_params.get("status")

        qs = PageComponent.objects.filter(page=page).exclude(
            component_type__in=["navbar", "footer"]
        )

        if status == "preview":
            # return only drafts
            return qs.filter(status="draft").order_by("order")
        return qs.filter(status="published").order_by("order")

    def perform_create(self, serializer):
        id = self.kwargs["id"]
        page = get_object_or_404(Page, id=id)

        # Fetch the order. Ensure it's the next available order or use the provided order.
        order = serializer.validated_data.get("order")
        if order is None:
            # Default to the next available order
            order = page.components.count()

        # Check if the order is valid (positive integer and doesn't conflict)
        if order < 0:
            return Response(
                {"detail": "Order cannot be negative."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Save the component with the associated page and the determined order
        serializer.save(page=page, order=order, status="draft")

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PageComponentRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PageComponentSerializer
    queryset = PageComponent.objects.all()

    def get_object(self):
        page_id = self.kwargs["page_id"]
        component_id = self.kwargs["component_id"]
        return get_object_or_404(PageComponent, page__id=page_id, id=component_id)

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

        serializer.save(status="draft", data=merged_data)


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

    def post(self, request):
        # Always create a draft when posting
        data = request.data.copy()
        data["component_type"] = "navbar"
        data["status"] = "draft"

        serializer = PageComponentSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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

    def post(self, request):
        # Always create a draft when posting
        data = request.data.copy()
        data["component_type"] = "footer"
        data["status"] = "draft"

        serializer = PageComponentSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
