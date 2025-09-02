from django.shortcuts import render
from rest_framework import generics
from .models import Whatsapp
from .serializers import WhatsappSerializer

# Create your views here.


class WhatsappListCreateAPIView(generics.ListCreateAPIView):
    queryset = Whatsapp.objects.all()
    serializer_class = WhatsappSerializer


class WhatsappRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Whatsapp.objects.all()
    serializer_class = WhatsappSerializer
