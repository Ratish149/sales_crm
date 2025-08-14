from django.shortcuts import render
from rest_framework import generics
from rest_framework import permissions
from .models import Website
from .serializers import WebsiteSerializer
# Create your views here.


class WebsiteListCreateView(generics.ListCreateAPIView):
    queryset = Website.objects.all()
    serializer_class = WebsiteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        return Website.objects.filter(user=self.request.user)


class WebsiteRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Website.objects.all()
    serializer_class = WebsiteSerializer
    permission_classes = [permissions.IsAuthenticated]
