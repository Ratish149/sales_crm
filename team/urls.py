from django.urls import path
from .views import TeamMemberListCreateView, TeamMemberRetrieveUpdateDestroyView

urlpatterns = [
    path('team-member/', TeamMemberListCreateView.as_view(),
         name='team-member-list-create'),
    path('team-member/<int:pk>/', TeamMemberRetrieveUpdateDestroyView.as_view(),
         name='team-member-retrieve-update-destroy'),
]
