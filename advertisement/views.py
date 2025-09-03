from rest_framework import generics
from .models import PopUp, PopUpForm
from .serializers import PopUpSerializer, PopUpFormSerializer

# Create your views here.


class PopUpCreateView(generics.ListCreateAPIView):
    queryset = PopUp.objects.all()
    serializer_class = PopUpSerializer


class PopUpRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PopUp.objects.all()
    serializer_class = PopUpSerializer


class PopUpFormCreateView(generics.ListCreateAPIView):
    queryset = PopUpForm.objects.all()
    serializer_class = PopUpFormSerializer


class PopUpFormRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PopUpForm.objects.all()
    serializer_class = PopUpFormSerializer
