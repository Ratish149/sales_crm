from rest_framework import generics
from .models import PopUp, PopUpForm
from .serializers import PopUpSerializer, PopUpFormSerializer

# Create your views here.
from rest_framework.pagination import PageNumberPagination


class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class PopUpCreateView(generics.ListCreateAPIView):
    queryset = PopUp.objects.all()
    serializer_class = PopUpSerializer
    pagination_class = CustomPagination


class PopUpRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PopUp.objects.all()
    serializer_class = PopUpSerializer


class PopUpFormCreateView(generics.ListCreateAPIView):
    queryset = PopUpForm.objects.all()
    serializer_class = PopUpFormSerializer
    pagination_class = CustomPagination


class PopUpFormRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PopUpForm.objects.all()
    serializer_class = PopUpFormSerializer
