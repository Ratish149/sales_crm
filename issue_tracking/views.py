from rest_framework import generics

from .models import Issue, IssueCategory
from .serializers import IssueCategorySerializer, IssueSerializer, IssueSerializer2

# Create your views here.

# Columns used by IssueCategorySerializer
_CATEGORY_FIELDS = ("id", "name")

# Columns used by IssueSerializer / IssueSerializer2 (FK column + related cols)
_ISSUE_FIELDS = (
    "id",
    "issue_category_id",  # the FK column on Issue
    "title",
    "description",
    "priority",
    "status",
    "created_at",
    "updated_at",
    "issue_category__id",  # pulled in by select_related
    "issue_category__name",
)


class IssueCategoryListCreateAPIView(generics.ListCreateAPIView):
    queryset = IssueCategory.objects.only(*_CATEGORY_FIELDS)
    serializer_class = IssueCategorySerializer


class IssueCategoryRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = IssueCategory.objects.only(*_CATEGORY_FIELDS)
    serializer_class = IssueCategorySerializer


class IssueListCreateAPIView(generics.ListCreateAPIView):
    # select_related covers the nested category on GET (IssueSerializer2);
    # only() limits columns fetched for both read and write paths.
    queryset = (
        Issue.objects
        .select_related("issue_category")
        .only(*_ISSUE_FIELDS)
        .order_by("-created_at")
    )

    def get_serializer_class(self):
        if self.request.method == "GET":
            return IssueSerializer2
        return IssueSerializer


class IssueRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Issue.objects.select_related("issue_category").only(*_ISSUE_FIELDS)
    serializer_class = IssueSerializer2
