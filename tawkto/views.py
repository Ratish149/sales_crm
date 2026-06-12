from rest_framework import generics

from .models import TawkTo
from .serializers import TawkToSerializer


class TawkToListCreateView(generics.ListCreateAPIView):
    queryset = TawkTo.objects.all()
    serializer_class = TawkToSerializer


class TawkToRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TawkTo.objects.all()
    serializer_class = TawkToSerializer
