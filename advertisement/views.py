from rest_framework import generics

# Create your views here.
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated

from sales_crm.authentication import TenantJWTAuthentication

from .models import Banner, BannerImage, PopUp, PopUpForm
from .serializers import (
    BannerImageSerializer,
    BannerSerializer,
    PopUpFormSerializer,
    PopUpSerializer,
)


class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class PopUpCreateView(generics.ListCreateAPIView):
    queryset = PopUp.objects.all().order_by("-created_at")
    serializer_class = PopUpSerializer

    def get_authenticators(self):
        if self.request.method == "POST":
            return [TenantJWTAuthentication()]
        return []  # No authentication for GET

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return super().get_permissions()


class PopUpRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PopUp.objects.all()
    serializer_class = PopUpSerializer
    authentication_classes = [TenantJWTAuthentication]
    permission_classes = [IsAuthenticated]


class PopUpFormCreateView(generics.ListCreateAPIView):
    queryset = PopUpForm.objects.all().order_by("-created_at")
    serializer_class = PopUpFormSerializer
    pagination_class = CustomPagination

    def get_authenticators(self):
        if self.request.method == "GET":
            return [TenantJWTAuthentication()]
        return []  # No authentication for GET

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return super().get_permissions()


class PopUpFormRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PopUpForm.objects.all()
    serializer_class = PopUpFormSerializer
    authentication_classes = [TenantJWTAuthentication]
    permission_classes = [IsAuthenticated]


class BannerImageListCreateView(generics.ListCreateAPIView):
    queryset = BannerImage.objects.all().order_by("-created_at")
    serializer_class = BannerImageSerializer

    def get_authenticators(self):
        if self.request.method == "POST":
            return [TenantJWTAuthentication()]
        return []  # No authentication for GET

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return super().get_permissions()


class BannerImageRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = BannerImage.objects.all()
    serializer_class = BannerImageSerializer
    authentication_classes = [TenantJWTAuthentication]
    permission_classes = [IsAuthenticated]


class BannerListCreateView(generics.ListCreateAPIView):
    queryset = Banner.objects.all().order_by("-created_at")
    serializer_class = BannerSerializer

    def get_authenticators(self):
        if self.request.method == "POST":
            return [TenantJWTAuthentication()]
        return []  # No authentication for GET

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return super().get_permissions()


class BannerRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Banner.objects.all()
    serializer_class = BannerSerializer
    authentication_classes = [TenantJWTAuthentication]
    permission_classes = [IsAuthenticated]
