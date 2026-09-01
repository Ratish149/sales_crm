from rest_framework import generics

from .models import FBPixel, MetaCommerce
from .serializers import FBPixelSerializer, MetaCommerceSerializer


class FBPixelListCreateView(generics.ListCreateAPIView):
    queryset = FBPixel.objects.all()
    serializer_class = FBPixelSerializer


class FBPixelRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = FBPixel.objects.all()
    serializer_class = FBPixelSerializer


class MetaCommerceListCreateView(generics.ListCreateAPIView):
    queryset = MetaCommerce.objects.all()
    serializer_class = MetaCommerceSerializer


class MetaCommerceRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MetaCommerce.objects.all()
    serializer_class = MetaCommerceSerializer

