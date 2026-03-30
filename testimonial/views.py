from django.shortcuts import render
from .models import Testimonial
from rest_framework import generics
from .serializers import TestimonialSerializer
from sales_crm.authentication import TenantJWTAuthentication
from rest_framework.permissions import IsAuthenticated
# Create your views here.


class TestimonialListCreateView(generics.ListCreateAPIView):
    queryset = Testimonial.objects.all()
    serializer_class = TestimonialSerializer

    def get_authenticators(self):
        if self.request.method == "POST":
            return [TenantJWTAuthentication()]
        return [] 

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return super().get_permissions()



class TestimonialRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Testimonial.objects.all()
    serializer_class = TestimonialSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [TenantJWTAuthentication]
