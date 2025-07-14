from django.shortcuts import render
from rest_framework import generics
from .models import Store
from .serializers import StoreSerializer
# Create your views here.

class StoreListCreateView(generics.ListCreateAPIView):
    queryset = Store.objects.all()
    serializer_class = StoreSerializer


