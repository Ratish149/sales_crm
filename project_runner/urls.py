from django.urls import path

from .views import StartProjectView, StopProjectView

urlpatterns = [
    path("start/", StartProjectView.as_view(), name="start-project"),
    path("stop/", StopProjectView.as_view(), name="stop-project"),
]
