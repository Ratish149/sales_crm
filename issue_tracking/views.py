from django.shortcuts import render
from rest_framework import generics
from .models import IssueCategory, Issue
from .serializers import IssueCategorySerializer, IssueSerializer
from issue_tracking import serializers
# Create your views here.


class IssueCategoryListCreateAPIView(generics.ListCreateAPIView):
    queryset = IssueCategory.objects.all()
    serializer_class = IssueCategorySerializer


class IssueCategoryRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = IssueCategory.objects.all()
    serializer_class = IssueCategorySerializer


class IssueListCreateAPIView(generics.ListCreateAPIView):
    queryset = Issue.objects.all()
    serializer_class = IssueSerializer

    def create(self, request, *args, **kwargs):
        serializer.save(reported_by=self.request.user)


class IssueRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Issue.objects.all()
    serializer_class = IssueSerializer
