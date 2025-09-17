from django.urls import path
from .views import YoutubeCreateView, YoutubeRetrieveUpdateDestroyView

urlpatterns = [
    path('youtube/', YoutubeCreateView.as_view(), name='youtube-create'),
    path('youtube/<int:pk>/', YoutubeRetrieveUpdateDestroyView.as_view(),
         name='youtube-retrieve-update-destroy'),
]
