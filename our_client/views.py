from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from sales_crm.authentication import TenantJWTAuthentication

from .models import OurClient
from .serializers import OurClientSerializer


class OurClientListCreateView(generics.ListCreateAPIView):
    queryset = OurClient.objects.only(
        "id", "name", "logo", "url", "created_at", "updated_at"
    )
    serializer_class = OurClientSerializer

    def get_authenticators(self):
        if self.request.method == "POST":
            return [TenantJWTAuthentication()]
        return []

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return super().get_permissions()


class OurClientRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = OurClient.objects.only(
        "id", "name", "logo", "url", "created_at", "updated_at"
    )
    serializer_class = OurClientSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [TenantJWTAuthentication]
