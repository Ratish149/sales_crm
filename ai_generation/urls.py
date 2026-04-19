from django.urls import path

from .views import GenerateBlogView, GeneratePortfolioView, GenerateServiceView

urlpatterns = [
    path("ai/generate-blog/", GenerateBlogView.as_view(), name="ai-generate-blog"),
    path(
        "ai/generate-service/",
        GenerateServiceView.as_view(),
        name="ai-generate-service",
    ),
    path(
        "ai/generate-portfolio/",
        GeneratePortfolioView.as_view(),
        name="ai-generate-portfolio",
    ),
]
