from django.shortcuts import render
from .models import Client, Domain
from rest_framework import generics
from .serializers import DomainSerializer
from rest_framework.pagination import PageNumberPagination
# Create your views here.


class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class DomainView(generics.ListCreateAPIView):
    queryset = Domain.objects.all()
    serializer_class = DomainSerializer
    pagination_class = CustomPagination


class DomainDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Domain.objects.all()
    serializer_class = DomainSerializer
