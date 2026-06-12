from rest_framework import generics

from .models import MSClarity
from .serializers import MSClaritySerializer


class MSClarityListCreateView(generics.ListCreateAPIView):
    queryset = MSClarity.objects.all()
    serializer_class = MSClaritySerializer


class MSClarityRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MSClarity.objects.all()
    serializer_class = MSClaritySerializer
