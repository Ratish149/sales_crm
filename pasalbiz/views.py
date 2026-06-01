import math

from django.utils.dateparse import parse_datetime
from django_tenants.utils import schema_context
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from pasalbiz.serializers import StorefrontProductSerializer, StoreListSerializer
from product.models import Product
from tenants.models import Client
from tenants.views import CustomPagination
from website.models import SiteConfig


class StoreListAPIView(generics.ListAPIView):
    """
    Public API view to retrieve a list of stores that have enabled pasalbiz.
    Only tenants with SiteConfig.enable_pasalbiz=True are returned.
    """

    permission_classes = [permissions.AllowAny]
    serializer_class = StoreListSerializer
    pagination_class = CustomPagination

    def get_queryset(self):
        all_clients = Client.objects.exclude(schema_name="public").order_by("id")

        enabled_ids = []
        for client in all_clients:
            try:
                with schema_context(client.schema_name):
                    config = SiteConfig.objects.first()
                    if config and config.enable_pasalbiz:
                        enabled_ids.append(client.id)
            except Exception:
                pass

        return Client.objects.filter(id__in=enabled_ids).order_by("id")


class StorefrontProductListView(APIView):
    """
    Public API view exposing products for the storefront catalog.
    Supports Stage 3 pagination (cursorless paging) and delta updates.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # 1. Parse parameters
        page_str = request.query_params.get("page", "1")
        per_page_str = request.query_params.get("per_page", "100")
        updated_after_str = request.query_params.get("updated_after")

        try:
            page = int(page_str)
            if page < 1:
                page = 1
        except ValueError:
            page = 1

        try:
            per_page = int(per_page_str)
            if per_page < 1:
                per_page = 100
            elif per_page > 100:
                per_page = 100
        except ValueError:
            per_page = 100

        # Query only published (active) products in current tenant context
        queryset = Product.objects.filter(status="active")

        # Apply updated_after filter if provided
        if updated_after_str:
            dt = parse_datetime(updated_after_str)
            if dt:
                queryset = queryset.filter(updated_at__gte=dt)

        total_items = queryset.count()
        total_pages = math.ceil(total_items / per_page) if total_items > 0 else 1

        # Retrieve page items
        start = (page - 1) * per_page
        end = start + per_page
        paginated_queryset = queryset.order_by("id")[start:end]

        serializer = StorefrontProductSerializer(
            paginated_queryset, many=True, context={"request": request}
        )

        response = Response(serializer.data, status=status.HTTP_200_OK)

        # Set pagination headers
        response["X-Total"] = str(total_items)
        response["X-Total-Pages"] = str(total_pages)

        # Build Link pagination header
        links = []
        base_url = request.build_absolute_uri(request.path)

        def get_page_url(page_num):
            import urllib.parse

            params = {"page": page_num, "per_page": per_page}
            if updated_after_str:
                params["updated_after"] = updated_after_str
            query_string = urllib.parse.urlencode(params)
            return f"{base_url}?{query_string}"

        if page < total_pages:
            links.append(f'<{get_page_url(page + 1)}>; rel="next"')
        if page > 1:
            links.append(f'<{get_page_url(page - 1)}>; rel="prev"')
        if total_pages > 0:
            links.append(f'<{get_page_url(total_pages)}>; rel="last"')

        if links:
            response["Link"] = ", ".join(links)

        return response
