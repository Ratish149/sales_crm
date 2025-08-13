from django.urls import path
from .views import WebsiteListCreateView, WebsiteRetrieveUpdateDestroyView

urlpatterns = [
    path('website/', WebsiteListCreateView.as_view(), name='website-list-create'),
    path('website/<int:pk>/', WebsiteRetrieveUpdateDestroyView.as_view(),
         name='website-retrieve-update-destroy'),
]
