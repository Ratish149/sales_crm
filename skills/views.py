from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from sales_crm.authentication import TenantJWTAuthentication

from .models import Skills
from .serializers import SkillsSerializer

SKILLS_QS = Skills.objects.only("id", "name", "description", "created_at", "updated_at")


class SkillsListCreateView(generics.ListCreateAPIView):
    queryset = SKILLS_QS.order_by("-created_at")
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
    queryset = SKILLS_QS
    serializer_class = SkillsSerializer

    def get_authenticators(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [TenantJWTAuthentication()]
        return []

    def get_permissions(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [IsAuthenticated()]
        return super().get_permissions()
