from rest_framework import generics

from .models import OurClient
from .serializers import OurClientSerializer

# Create your views here.


class OurClientListCreateView(generics.ListCreateAPIView):
    queryset = OurClient.objects.all()
    serializer_class = OurClientSerializer


class OurClientRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = OurClient.objects.all()
    serializer_class = OurClientSerializer
