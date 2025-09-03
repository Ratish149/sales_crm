from rest_framework import generics
from .models import PopUp
from .serializers import PopUpSerializer

# Create your views here.


class PopUpCreateView(generics.ListCreateAPIView):
    queryset = PopUp.objects.all()
    serializer_class = PopUpSerializer


class PopUpRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PopUp.objects.all()
    serializer_class = PopUpSerializer
