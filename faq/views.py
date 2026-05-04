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
    queryset = FAQCategory.objects.all()
    serializer_class = FAQCategorySerializer


class FAQCategoryRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = FAQCategory.objects.all()
    serializer_class = FAQCategorySerializer


class FAQFilterSet(filters.FilterSet):
    category = filters.CharFilter(field_name="category__id", lookup_expr="exact")

    class Meta:
        model = FAQ
        fields = {
            "category": ["exact"],
        }


class FAQListCreateView(generics.ListCreateAPIView):
    queryset = FAQ.objects.all()
    serializer_class = FAQSerializer
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = FAQFilterSet


class FAQRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = FAQ.objects.all()
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
        created_faqs = []

        for item in faqs_data:
            faq = FAQ.objects.create(**item)
            created_faqs.append(faq)

        response_data = FAQSerializer(created_faqs, many=True).data
        return Response(
            {"created": len(created_faqs), "faqs": response_data},
            status=status.HTTP_201_CREATED,
        )
