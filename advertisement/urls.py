from django.urls import path
from .views import PopUpCreateView, PopUpRetrieveUpdateDestroyView, PopUpFormCreateView, PopUpFormRetrieveUpdateDestroyView

urlpatterns = [
    path('popup/', PopUpCreateView.as_view(), name='popup-create'),
    path('popup/<int:pk>/', PopUpRetrieveUpdateDestroyView.as_view(),
         name='popup-retrieve-update-destroy'),
    path('popup-form/', PopUpFormCreateView.as_view(), name='popup-form-create'),
    path('popup-form/<int:pk>/', PopUpFormRetrieveUpdateDestroyView.as_view(),
         name='popup-form-retrieve-update-destroy'),
]
