from django.urls import path
from .views import ContactCreateView, ContactRetrieveUpdateDestroyView, NewsLetterCreateView, NewsLetterRetrieveUpdateDestroyView

urlpatterns = [
    path('contact/', ContactCreateView.as_view(), name='contact-create'),
    path('contact/<int:pk>/', ContactRetrieveUpdateDestroyView.as_view(),
         name='contact-retrieve-update-destroy'),
    path('newsletter/', NewsLetterCreateView.as_view(), name='newsletter-create'),
    path('newsletter/<int:pk>/', NewsLetterRetrieveUpdateDestroyView.as_view(),
         name='newsletter-retrieve-update-destroy'),
]
