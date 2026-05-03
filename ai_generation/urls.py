from django.urls import path

from .views import (
    GenerateBlogView,
    GenerateFAQView,
    GeneratePortfolioView,
    GenerateProductFromImageView,
    GenerateServiceView,
    GenerateTestimonialView,
)

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
    path(
        "ai/generate-product/",
        GenerateProductFromImageView.as_view(),
        name="ai-generate-product",
    ),
    path(
        "ai/generate-testimonial/",
        GenerateTestimonialView.as_view(),
        name="ai-generate-testimonial",
    ),
    path(
        "ai/generate-faq/",
        GenerateFAQView.as_view(),
        name="ai-generate-faq",
    ),
]
