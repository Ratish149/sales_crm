from django_filters import rest_framework as django_filters
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from sales_crm.authentication import TenantJWTAuthentication

from .models import TeamMember, TeamMemberCategory
from .serializers import TeamMemberCategorySerializer, TeamMemberSerializer

# Create your views here.


class TeamMemberCategoryListCreateView(generics.ListCreateAPIView):
    queryset = TeamMemberCategory.objects.all()
    serializer_class = TeamMemberCategorySerializer

    def get_authenticators(self):
        if self.request.method == "POST":
            return [TenantJWTAuthentication()]
        return []

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return super().get_permissions()


class TeamMemberCategoryRetrieveUpdateDestroyView(
    generics.RetrieveUpdateDestroyAPIView
):
    queryset = TeamMemberCategory.objects.all()
    serializer_class = TeamMemberCategorySerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [TenantJWTAuthentication]


class TeamMemberFilterSet(django_filters.FilterSet):
    category = django_filters.CharFilter(field_name="category__id", lookup_expr="exact")

    class Meta:
        model = TeamMember
        fields = {
            "category": ["exact"],
        }


class TeamMemberListCreateView(generics.ListCreateAPIView):
    queryset = TeamMember.objects.all()
    serializer_class = TeamMemberSerializer
    filter_backends = [django_filters.DjangoFilterBackend]
    filterset_class = TeamMemberFilterSet

    def get_authenticators(self):
        if self.request.method == "POST":
            return [TenantJWTAuthentication()]
        return []

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return super().get_permissions()


class TeamMemberRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TeamMember.objects.all()
    serializer_class = TeamMemberSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [TenantJWTAuthentication]
