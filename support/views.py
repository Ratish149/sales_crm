from django_filters import rest_framework as django_filters
from rest_framework import generics
from rest_framework.pagination import PageNumberPagination

from .models import FAQ, Contact, FAQCategory, NepdoraTestimonial, Newsletter
from .serializers import (
    ContactSerializer,
    FAQCategorySerializer,
    FAQSerializer,
    NepdoraTestimonialSerializer,
    NewsletterSerializer,
)


# Create your views here.
class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


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


class NepdoraTestimonialRetrieveUpdateDestroyView(
    generics.RetrieveUpdateDestroyAPIView
):
    queryset = NepdoraTestimonial.objects.all()
    serializer_class = NepdoraTestimonialSerializer


class ContactListCreateView(generics.ListCreateAPIView):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    pagination_class = CustomPagination


class ContactRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer


class NewsletterListCreateView(generics.ListCreateAPIView):
    queryset = Newsletter.objects.all()
    serializer_class = NewsletterSerializer
    pagination_class = CustomPagination


class NewsletterRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Newsletter.objects.all()
    serializer_class = NewsletterSerializer
