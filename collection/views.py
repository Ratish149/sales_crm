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
            filter_value = self.request.query_params.get(field_name)

            if filter_value is not None:
                # Filter by exact match in JSON data field
                # Using JSONField lookup: data__field_name
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
        serializer.save(collection=collection)

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
