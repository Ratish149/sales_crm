from rest_framework import generics

from .models import Video
from .serializers import VideoSerializer
from sales_crm.authentication import TenantJWTAuthentication
from rest_framework.permissions import IsAuthenticated
# Create your views here.


class VideoListCreateView(generics.ListCreateAPIView):
    queryset = Video.objects.all()
    serializer_class = VideoSerializer

    def get_authenticators(self):
        if self.request.method == "POST":
            return [TenantJWTAuthentication()]
        return [] 

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return super().get_permissions()

class VideoRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Video.objects.all()
    serializer_class = VideoSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [TenantJWTAuthentication]
