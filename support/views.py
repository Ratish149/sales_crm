from django_filters import rest_framework as django_filters
from rest_framework import generics

from .models import FAQ, FAQCategory, NepdoraTestimonial
from .serializers import FAQCategorySerializer, FAQSerializer, NepdoraTestimonialSerializer

# Create your views here.


class FAQCategoryListCreateView(generics.ListCreateAPIView):
    queryset = FAQCategory.objects.all()
    serializer_class = FAQCategorySerializer


class FAQCategoryRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = FAQCategory.objects.all()
    serializer_class = FAQCategorySerializer


class FAQFilterSet(django_filters.FilterSet):
    category = django_filters.CharFilter(field_name="category__id", lookup_expr="exact")

    class Meta:
        model = FAQ
        fields = {
            "category": ["exact"],
        }


class FAQListCreateView(generics.ListCreateAPIView):
    queryset = FAQ.objects.all()
    serializer_class = FAQSerializer
    filter_backends = [django_filters.DjangoFilterBackend]
    filterset_class = FAQFilterSet


class FAQRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = FAQ.objects.all()
    serializer_class = FAQSerializer


class NepdoraTestimonialListCreateView(generics.ListCreateAPIView):
    queryset = NepdoraTestimonial.objects.all()
    serializer_class = NepdoraTestimonialSerializer


class NepdoraTestimonialRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = NepdoraTestimonial.objects.all()
    serializer_class = NepdoraTestimonialSerializer