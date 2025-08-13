from django.shortcuts import render
from rest_framework import generics
from .models import SiteModel
from .serializers import StoreSerializer
from rest_framework.permissions import IsAuthenticated
# Create your views here.


class StoreListCreateView(generics.ListCreateAPIView):
    queryset = SiteModel.objects.all()
    serializer_class = StoreSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SiteModel.objects.filter(user=self.request.user)
