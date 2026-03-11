from django.urls import path
from .views import SkillsListCreateView, SkillsRetrieveUpdateDestroyView

urlpatterns = [
    path("skills/", SkillsListCreateView.as_view(), name="skills-list-create"),
    path(
        "skills/<int:pk>/",
        SkillsRetrieveUpdateDestroyView.as_view(),
        name="skills-retrieve-update-destroy",
    ),
]
