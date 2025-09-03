from django.urls import path
from .views import PopUpCreateView, PopUpRetrieveUpdateDestroyView

urlpatterns = [
    path('popup/', PopUpCreateView.as_view(), name='popup-create'),
    path('popup/<int:pk>/', PopUpRetrieveUpdateDestroyView.as_view(),
         name='popup-retrieve-update-destroy'),
]
