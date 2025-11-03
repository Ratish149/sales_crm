from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import Facebook
from .serializers import FacebookSerializer


class FacebookListCreateView(generics.ListCreateAPIView):
    queryset = Facebook.objects.filter(is_enabled=True)
    serializer_class = FacebookSerializer
    permission_classes = [IsAuthenticated]


class FacebookRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Facebook.objects.all()
    serializer_class = FacebookSerializer
