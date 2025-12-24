import os

import resend
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics

from sales_crm.pagination import CustomPagination

from .models import Collection, CollectionData
from .serializers import CollectionDataSerializer, CollectionSerializer


class CollectionListCreateView(generics.ListCreateAPIView):
    """
    List all collections or create a new one.
    GET: List all collections
    POST: Create a new collection
    """

    queryset = Collection.objects.all()
    serializer_class = CollectionSerializer


class CollectionRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a collection by slug.
    GET: Retrieve collection details
    PUT/PATCH: Update collection
    DELETE: Delete collection
    """

    queryset = Collection.objects.all()
    serializer_class = CollectionSerializer
    lookup_field = "slug"


class CollectionDataListCreateView(generics.ListCreateAPIView):
    """
    List all data instances for a specific collection or create a new one.
    GET: List all data for the collection (supports filtering by filterable fields)
    POST: Create new data instance
    """

    serializer_class = CollectionDataSerializer
    pagination_class = CustomPagination

    def get_queryset(self):
        """Filter data by the collection slug from URL and apply dynamic filters"""
        slug = self.kwargs.get("slug")
        collection = get_object_or_404(Collection, slug=slug)
        queryset = CollectionData.objects.filter(collection=collection)

        # Apply dynamic filtering based on filterable fields (default + custom)
        all_fields = collection.get_all_fields()
        filterable_fields = [
            field for field in all_fields if field.get("filterable", False)
        ]

        for field_def in filterable_fields:
            field_name = field_def["name"]
            field_type = field_def["type"]
            filter_value = self.request.query_params.get(field_name)

            if filter_value is not None:
                # Determine filter lookup based on field type
                # For text-based fields and model (which stores strings), use iexact
                if field_type in ["text", "slug", "email", "url", "model"]:
                    filter_key = f"data__{field_name}__iexact"
                else:
                    # For numbers, booleans, dates, etc., use exact match
                    filter_key = f"data__{field_name}"

                queryset = queryset.filter(**{filter_key: filter_value})

        # Apply search across all searchable fields
        search_query = self.request.query_params.get("search")
        if search_query:
            searchable_fields = [
                field for field in all_fields if field.get("searchable", False)
            ]
            if searchable_fields:
                q_objects = Q()
                for field_def in searchable_fields:
                    field_name = field_def["name"]
                    # Search using icontains in JSON data field
                    filter_key = f"data__{field_name}__icontains"
                    q_objects |= Q(**{filter_key: search_query})

                queryset = queryset.filter(q_objects)

        return queryset

    def perform_create(self, serializer):
        """Automatically set the collection from URL slug"""
        slug = self.kwargs.get("slug")
        collection = get_object_or_404(Collection, slug=slug)
        instance = serializer.save(collection=collection)

        # Send email if enabled
        if collection.send_email and collection.admin_email:
            resend.api_key = os.getenv("RESEND_API_KEY")

            # Format data for email
            data_html = "<ul>"

            # Add name, slug, and description/content from default fields if present
            name = instance.data.get("name")
            if name:
                data_html += f"<li><strong>Name:</strong> {name}</li>"

            slug_val = instance.data.get("slug")
            if slug_val:
                data_html += f"<li><strong>Slug:</strong> {slug_val}</li>"

            # User refers to 'content' default field as description
            description = instance.data.get("description") or instance.data.get(
                "content"
            )
            if description:
                data_html += f"<li><strong>Description:</strong> {description}</li>"

            # Add remaining fields
            for key, value in instance.data.items():
                if key in ["name", "slug", "description", "content"]:
                    continue
                data_html += f"<li><strong>{key}:</strong> {value}</li>"
            data_html += "</ul>"

            html_body = f"""
            <h2>New Submission for {collection.name}</h2>
            <p>You have received a new submission.</p>
            {data_html}
            """

            params = {
                "from": "Nepdora <nepdora@baliyoventures.com>",
                "to": [collection.admin_email],
                "subject": f"New Submission Received: {collection.name}",
                "html": html_body,
            }

            try:
                resend.Emails.send(params)
            except Exception as e:
                # Log error or handle silently to not disrupt the response
                print(f"Failed to send email: {str(e)}")

    def get_serializer_context(self):
        """Pass collection to serializer context for validation"""
        context = super().get_serializer_context()
        slug = self.kwargs.get("slug")
        # Only try to get collection if slug is present (to avoid issues with schema generation etc)
        if slug:
            context["collection"] = get_object_or_404(Collection, slug=slug)
        return context


class CollectionDataRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a specific data instance.
    GET: Retrieve data details
    PUT/PATCH: Update data
    DELETE: Delete data
    """

    serializer_class = CollectionDataSerializer
    lookup_field = "pk"

    def get_queryset(self):
        """Filter data by collection slug and ensure data belongs to the collection"""
        slug = self.kwargs.get("slug")
        collection = get_object_or_404(Collection, slug=slug)
        return CollectionData.objects.filter(collection=collection)

    def perform_update(self, serializer):
        """Ensure collection is set correctly on update"""
        slug = self.kwargs.get("slug")
        collection = get_object_or_404(Collection, slug=slug)
        serializer.save(collection=collection)
