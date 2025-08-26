from rest_framework import generics
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from .models import Order
from .serializers import OrderSerializer

# List and Create Orders
from rest_framework.pagination import PageNumberPagination

# Create your views here.


class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class OrderListCreateAPIView(generics.ListCreateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    pagination_class = CustomPagination

# Retrieve, Update, Delete single Order


class OrderRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
