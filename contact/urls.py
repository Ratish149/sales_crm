from django.urls import path
from .views import ContactCreateView, ContactRetrieveUpdateDestroyView

urlpatterns = [
    path('contact/', ContactCreateView.as_view(), name='contact-create'),
    path('contact/<int:pk>/', ContactRetrieveUpdateDestroyView.as_view(),
         name='contact-retrieve-update-destroy'),
]
