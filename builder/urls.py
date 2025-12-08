from django.urls import path

from .views import BuilderIDEView

urlpatterns = [
    path("", BuilderIDEView.as_view(), name="builder_ide"),
]
