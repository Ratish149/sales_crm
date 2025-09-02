from django.urls import path
from .views import WhatsappListCreateAPIView, WhatsappRetrieveUpdateDestroyAPIView

urlpatterns = [
    path('whatsapp/', WhatsappListCreateAPIView.as_view(),
         name='whatsapp-list-create'),
    path('whatsapp/<int:pk>/', WhatsappRetrieveUpdateDestroyAPIView.as_view(),
         name='whatsapp-retrieve-update-destroy'),
]
