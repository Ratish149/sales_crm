from django.shortcuts import get_object_or_404
from .models import Page, PageComponent
from .serializers import PageComponentSerializer, PageSerializer
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status


class PageListCreateView(generics.ListCreateAPIView):
    """
    List all pages OR add a new page.
    URL: /api/pages/
    """
    serializer_class = PageSerializer
    queryset = Page.objects.all()

    def perform_create(self, serializer):
        serializer.save()


class PageRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a single page.
    URL: /api/pages/<page_id>/
    """
    serializer_class = PageSerializer
    queryset = Page.objects.all()
    


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
        return Response({"detail": "Navbar not found"}, status=status.HTTP_404_NOT_FOUND)

    # POST -> create navbar
    def post(self, request, *args, **kwargs):
        if self.get_object():
            return Response({"detail": "Navbar already exists"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(component_type="navbar")
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # PATCH -> update navbar
    def patch(self, request, *args, **kwargs):
        obj = self.get_object()
        if not obj:
            return Response({"detail": "Navbar not found"}, status=status.HTTP_404_NOT_FOUND)

        new_data = request.data.get("data", {})
        if new_data:
            current_data = obj.data or {}
            current_data.update(new_data)
            request.data["data"] = current_data

        serializer = self.get_serializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    # DELETE -> delete navbar
    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        if not obj:
            return Response({"detail": "Navbar not found"}, status=status.HTTP_404_NOT_FOUND)
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
        return Response({"detail": "Footer not found"}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, *args, **kwargs):
        if self.get_object():
            return Response({"detail": "Footer already exists"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(component_type="footer")
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def patch(self, request, *args, **kwargs):
        obj = self.get_object()
        if not obj:
            return Response({"detail": "Footer not found"}, status=status.HTTP_404_NOT_FOUND)

        new_data = request.data.get("data", {})
        if new_data:
            current_data = obj.data or {}
            current_data.update(new_data)
            request.data["data"] = current_data

        serializer = self.get_serializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        if not obj:
            return Response({"detail": "Footer not found"}, status=status.HTTP_404_NOT_FOUND)
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
        return PageComponent.objects.filter(page__slug=slug).exclude(component_type__in=["navbar", "footer"])

    def perform_create(self, serializer):
        slug = self.kwargs["slug"]
        page = get_object_or_404(Page, slug=slug)
        order = serializer.validated_data.get("order", page.components.count())
        serializer.save(page=page, order=order)


class PageComponentByTypeView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a single component by type (e.g. navbar, hero).
    URL: /api/pages/<page_id>/components/<type>/
    """
    serializer_class = PageComponentSerializer

    def get_object(self):
        slug = self.kwargs["slug"]
        id = self.kwargs["id"]
        return get_object_or_404(PageComponent, page__slug=slug, id=id)

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

        return super().partial_update(request, *args, **kwargs)
