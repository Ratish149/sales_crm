from django.shortcuts import render
from .models import TeamMember
from rest_framework import generics
from .serializers import TeamMemberSerializer
from sales_crm.authentication import TenantJWTAuthentication
from rest_framework.permissions import IsAuthenticated
# Create your views here.


class TeamMemberListCreateView(generics.ListCreateAPIView):
    queryset = TeamMember.objects.all()
    serializer_class = TeamMemberSerializer

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
