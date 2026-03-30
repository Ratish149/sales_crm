from rest_framework import generics

from .models import OurClient
from .serializers import OurClientSerializer

from sales_crm.authentication import TenantJWTAuthentication
from rest_framework.permissions import IsAuthenticated
# Create your views here.


class OurClientListCreateView(generics.ListCreateAPIView):
    queryset = OurClient.objects.all()
    serializer_class = OurClientSerializer

    def get_authenticators(self):
        if self.request.method == "POST":
            return [TenantJWTAuthentication()]
        return []  # No authentication for GET

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return super().get_permissions()


class OurClientRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = OurClient.objects.all()
    serializer_class = OurClientSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [TenantJWTAuthentication]