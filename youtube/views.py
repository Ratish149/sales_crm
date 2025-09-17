from django.shortcuts import render
from rest_framework import generics
from .models import Youtube
from .serializers import YoutubeSerializer
# Create your views here.


class YoutubeCreateView(generics.ListCreateAPIView):
    queryset = Youtube.objects.all()
    serializer_class = YoutubeSerializer


class YoutubeRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Youtube.objects.all()
    serializer_class = YoutubeSerializer
