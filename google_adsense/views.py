from rest_framework import generics

from .models import GoogleAdSense
from .serializers import GoogleAdSenseSerializer


class GoogleAdSenseListCreateView(generics.ListCreateAPIView):
    queryset = GoogleAdSense.objects.all()
    serializer_class = GoogleAdSenseSerializer


class GoogleAdSenseRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = GoogleAdSense.objects.all()
    serializer_class = GoogleAdSenseSerializer
