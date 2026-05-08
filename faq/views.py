from django.db import transaction
from django_filters import rest_framework as filters
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import FAQ, FAQCategory
from .serializers import (
    BulkCreateFAQSerializer,
    FAQCategorySerializer,
    FAQSerializer,
)

# Create your views here.


class FAQCategoryListCreateView(generics.ListCreateAPIView):
    queryset = FAQCategory.objects.only("id", "name")
    serializer_class = FAQCategorySerializer


class FAQCategoryRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = FAQCategory.objects.only("id", "name")
    serializer_class = FAQCategorySerializer


class FAQFilterSet(filters.FilterSet):
    category = filters.CharFilter(field_name="category__id", lookup_expr="exact")

    class Meta:
        model = FAQ
        fields = {
            "category": ["exact"],
        }


class FAQListCreateView(generics.ListCreateAPIView):
    queryset = FAQ.objects.select_related("category").only(
        "id", "question", "answer", "category__id", "category__name"
    )
    serializer_class = FAQSerializer
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = FAQFilterSet


class FAQRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = FAQ.objects.select_related("category").only(
        "id", "question", "answer", "category__id", "category__name"
    )
    serializer_class = FAQSerializer


class BulkCreateFAQView(APIView):
    """
    POST /api/faq/bulk-create/
    Body: { "faqs": [ { "question": "...", "answer": "..." }, ... ] }
    """

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = BulkCreateFAQSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        faqs_data = serializer.validated_data.get("faqs", [])

        new_faqs = [FAQ(**item) for item in faqs_data]
        created_faqs = FAQ.objects.bulk_create(new_faqs, ignore_conflicts=False)

        # Re-fetch with select_related so the serializer has category data
        created_ids = [faq.pk for faq in created_faqs]
        qs = (
            FAQ.objects
            .select_related("category")
            .only("id", "question", "answer", "category__id", "category__name")
            .filter(pk__in=created_ids)
        )

        response_data = FAQSerializer(qs, many=True).data
        return Response(
            {"created": len(created_faqs), "faqs": response_data},
            status=status.HTTP_201_CREATED,
        )
