from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response

from .models import Page, PageComponent, Theme
from .serializers import PageComponentSerializer, PageSerializer, ThemeSerializer


class ThemeListCreateView(generics.ListCreateAPIView):
    """
    List all themes OR add a new theme.
    URL: /api/themes/
    """

    serializer_class = ThemeSerializer

    def get_queryset(self):
        status_param = self.request.query_params.get("status")
        if status_param == "preview":
            qs = Theme.objects.all()
        else:
            qs = Theme.objects.filter(status="published")
        return qs

    def perform_create(self, serializer):
        serializer.save(status="draft")


class ThemeRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a single theme.
    URL: /api/themes/<theme_id>/
    """

    serializer_class = ThemeSerializer
    queryset = Theme.objects.all()

    def perform_update(self, serializer):
        if "status" not in serializer.validated_data:
            serializer.validated_data["status"] = "draft"
        serializer.save()


class PageListCreateView(generics.ListCreateAPIView):
    serializer_class = PageSerializer

    def get_queryset(self):
        status_param = self.request.query_params.get("status")
        if status_param == "preview":
            qs = Page.objects.all()
        else:
            qs = Page.objects.filter(status="published")
        return qs

    def perform_create(self, serializer):
        serializer.save(status="draft")


class PageRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a single page.
    URL: /api/pages/<page_id>/
    """

    serializer_class = PageSerializer
    queryset = Page.objects.all()
    lookup_field = "slug"

    def perform_update(self, serializer):
        if "status" not in serializer.validated_data:
            serializer.validated_data["status"] = "draft"
        serializer.save()


class NavbarView(generics.GenericAPIView):
    serializer_class = PageComponentSerializer

    def get_object(self):
        return PageComponent.objects.filter(component_type="navbar").first()

    # GET -> retrieve navbar
    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj:
            serializer = self.get_serializer(obj)
            return Response(serializer.data)
        return Response(
            {"detail": "Navbar not found"}, status=status.HTTP_404_NOT_FOUND
        )

    # POST -> create navbar
    def post(self, request, *args, **kwargs):
        if self.get_object():
            return Response(
                {"detail": "Navbar already exists"}, status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(component_type="navbar")
        serializer.instance.status = "draft"
        serializer.instance.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # PATCH -> update navbar
    def patch(self, request, *args, **kwargs):
        obj = self.get_object()
        if not obj:
            return Response(
                {"detail": "Navbar not found"}, status=status.HTTP_404_NOT_FOUND
            )

        new_data = request.data.get("data", {})
        if new_data:
            current_data = obj.data or {}
            current_data.update(new_data)
            request.data["data"] = current_data
        if "status" not in request.data:
            request.data["status"] = "draft"

        serializer = self.get_serializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    # DELETE -> delete navbar
    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        if not obj:
            return Response(
                {"detail": "Navbar not found"}, status=status.HTTP_404_NOT_FOUND
            )
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# -------------------- FOOTER --------------------
class FooterView(generics.GenericAPIView):
    serializer_class = PageComponentSerializer

    def get_object(self):
        return PageComponent.objects.filter(component_type="footer").first()

    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj:
            serializer = self.get_serializer(obj)
            return Response(serializer.data)
        return Response(
            {"detail": "Footer not found"}, status=status.HTTP_404_NOT_FOUND
        )

    def post(self, request, *args, **kwargs):
        if self.get_object():
            return Response(
                {"detail": "Footer already exists"}, status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(component_type="footer")
        serializer.instance.status = "draft"
        serializer.instance.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def patch(self, request, *args, **kwargs):
        obj = self.get_object()
        if not obj:
            return Response(
                {"detail": "Footer not found"}, status=status.HTTP_404_NOT_FOUND
            )

        new_data = request.data.get("data", {})
        if new_data:
            current_data = obj.data or {}
            current_data.update(new_data)
            request.data["data"] = current_data
        if "status" not in request.data:
            request.data["status"] = "draft"

        serializer = self.get_serializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        if not obj:
            return Response(
                {"detail": "Footer not found"}, status=status.HTTP_404_NOT_FOUND
            )
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PageComponentListCreateView(generics.ListCreateAPIView):
    """
    List all components for a page OR add a new component.
    URL: /api/pages/<page_id>/components/
    """

    serializer_class = PageComponentSerializer

    def get_queryset(self):
        slug = self.kwargs["slug"]
        status_param = self.request.query_params.get("status")
        qs = PageComponent.objects.filter(page__slug=slug).exclude(
            component_type__in=["navbar", "footer"]
        )
        if status_param == "preview":
            qs = qs.all()
        else:
            qs = qs.filter(page__status="published")
        return qs

    def perform_create(self, serializer):
        slug = self.kwargs["slug"]
        page = get_object_or_404(Page, slug=slug)
        order = serializer.validated_data.get("order", page.components.count())
        serializer.save(page=page, order=order, status="draft")


class PageComponentByTypeView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a single component by type (e.g. navbar, hero).
    URL: /api/pages/<page_id>/components/<type>/
    """

    serializer_class = PageComponentSerializer

    def get_object(self):
        slug = self.kwargs["slug"]
        component_id = self.kwargs["component_id"]
        return get_object_or_404(
            PageComponent, page__slug=slug, component_id=component_id
        )

    def perform_update(self, serializer):
        if "status" not in serializer.validated_data:
            serializer.validated_data["status"] = "draft"
        serializer.save()

    def partial_update(self, request, *args, **kwargs):
        """
        Allows merging JSON data instead of replacing the whole 'data' field.
        Example: PATCH { "data": {"logoText": "New Logo"} }
        """
        instance = self.get_object()
        new_data = request.data.get("data")

        if new_data and isinstance(new_data, dict):
            current_data = instance.data or {}
            current_data.update(new_data)
            request.data["data"] = current_data
        if "status" not in request.data:
            request.data["status"] = "draft"

        return super().partial_update(request, *args, **kwargs)


class PublishAllView(generics.GenericAPIView):
    """
    Publish all draft items (themes, pages, components) in one API call.
    URL: /api/publish-all/
    """

    def post(self, request, *args, **kwargs):
        # Publish all draft themes
        Theme.objects.filter(status="draft").update(status="published")
        # Publish all draft pages
        Page.objects.filter(status="draft").update(status="published")
        # Publish all draft components
        PageComponent.objects.filter(status="draft").update(status="published")
        return Response({"detail": "All draft items have been published successfully"})
