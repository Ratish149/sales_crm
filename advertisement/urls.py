from django.urls import path
from .views import PopUpCreateView, PopUpRetrieveUpdateDestroyView, PopUpFormCreateView, PopUpFormRetrieveUpdateDestroyView, BannerImageListCreateView, BannerImageRetrieveUpdateDestroyView, BannerListCreateView, BannerRetrieveUpdateDestroyView

urlpatterns = [
    path('popup/', PopUpCreateView.as_view(), name='popup-create'),
    path('popup/<int:pk>/', PopUpRetrieveUpdateDestroyView.as_view(),
         name='popup-retrieve-update-destroy'),
    path('popup-form/', PopUpFormCreateView.as_view(), name='popup-form-create'),
    path('popup-form/<int:pk>/', PopUpFormRetrieveUpdateDestroyView.as_view(),
         name='popup-form-retrieve-update-destroy'),
    path('banner-images/', BannerImageListCreateView.as_view(),
         name='banner-image-list-create'),
    path('banner-images/<int:pk>/', BannerImageRetrieveUpdateDestroyView.as_view(),
         name='banner-image-retrieve-update-destroy'),
    path('banners/', BannerListCreateView.as_view(), name='banner-list-create'),
    path('banners/<int:pk>/', BannerRetrieveUpdateDestroyView.as_view(),
         name='banner-retrieve-update-destroy'),
]
