from django.shortcuts import render
from rest_framework import generics
from .models import Whatsapp
from .serializers import WhatsappSerializer
from sales_crm.authentication import TenantJWTAuthentication
from rest_framework.permissions import IsAuthenticated

# Create your views here.


class WhatsappListCreateAPIView(generics.ListCreateAPIView):
    queryset = Whatsapp.objects.all()
    serializer_class = WhatsappSerializer

    def get_authenticators(self):
        if self.request.method == "POST":
            return [TenantJWTAuthentication()]
        return [] 

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return super().get_permissions()


class WhatsappRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Whatsapp.objects.all()
    serializer_class = WhatsappSerializer

    def get_authenticators(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [TenantJWTAuthentication()]
        return [] 

    def get_permissions(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [IsAuthenticated()]
        return super().get_permissions()
