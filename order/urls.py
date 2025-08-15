from django.urls import path
from .views import OrderListCreateAPIView, OrderRetrieveUpdateDestroyAPIView

urlpatterns = [
    path('order/', OrderListCreateAPIView.as_view(), name='order-list-create'),
    path('order/<int:pk>/', OrderRetrieveUpdateDestroyAPIView.as_view(),
         name='order-retrieve-update-destroy'),
]
