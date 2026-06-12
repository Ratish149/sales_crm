from rest_framework import generics

from .models import FBPixel
from .serializers import FBPixelSerializer


class FBPixelListCreateView(generics.ListCreateAPIView):
    queryset = FBPixel.objects.all()
    serializer_class = FBPixelSerializer


class FBPixelRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = FBPixel.objects.all()
    serializer_class = FBPixelSerializer
