from rest_framework import generics
from .models import Skills
from .serializers import SkillsSerializer
from sales_crm.authentication import TenantJWTAuthentication
from rest_framework.permissions import IsAuthenticated



class SkillsListCreateView(generics.ListCreateAPIView):
    queryset = Skills.objects.all()
    serializer_class = SkillsSerializer

    def get_authenticators(self):
        if self.request.method == "POST":
            return [TenantJWTAuthentication()]
        return [] 

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return super().get_permissions()


class SkillsRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Skills.objects.all()
    serializer_class = SkillsSerializer
    
    def get_authenticators(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [TenantJWTAuthentication()]
        return [] 

    def get_permissions(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [IsAuthenticated()]
        return super().get_permissions()
