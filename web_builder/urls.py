from django.urls import path

from .views import BuildWebsiteView

urlpatterns = [
    path("build/", BuildWebsiteView.as_view(), name="web_builder_build"),
]
