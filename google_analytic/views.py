from rest_framework import generics

from .models import GoogleAnalytic
from .serializers import GoogleAnalyticSerializer


class GoogleAnalyticListCreateView(generics.ListCreateAPIView):
    queryset = GoogleAnalytic.objects.all()
    serializer_class = GoogleAnalyticSerializer


class GoogleAnalyticRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = GoogleAnalytic.objects.all()
    serializer_class = GoogleAnalyticSerializer
