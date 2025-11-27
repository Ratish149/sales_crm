from rest_framework import generics, status
from rest_framework.response import Response

from .models import Issue, IssueCategory
from .serializers import IssueCategorySerializer, IssueSerializer, IssueSerializer2

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
        serializer = self.get_serializer(data=request.data)  # instantiate
        serializer.is_valid(raise_exception=True)  # validate
        serializer.save()  # save with user
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get_serializer_class(self):
        if self.request.method == "GET":
            return IssueSerializer2
        return IssueSerializer


class IssueRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Issue.objects.all()
    serializer_class = IssueSerializer
