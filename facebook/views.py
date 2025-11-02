from rest_framework import generics

from .models import Facebook
from .serializers import FacebookSerializer


class FacebookListCreateView(generics.ListCreateAPIView):
    queryset = Facebook.objects.all()
    serializer_class = FacebookSerializer


class FacebookRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Facebook.objects.all()
    serializer_class = FacebookSerializer
