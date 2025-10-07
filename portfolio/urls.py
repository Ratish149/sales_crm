from django.urls import path

from .views import (
    PortfolioCategoryListCreateAPIView,
    PortfolioCategoryRetrieveUpdateDestroyAPIView,
    PortfolioListCreateAPIView,
    PortfolioRetrieveUpdateDestroyAPIView,
    PortfolioTagsListCreateAPIView,
    PortfolioTagsRetrieveUpdateDestroyAPIView,
)

urlpatterns = [
    path("portfolio/category/", PortfolioCategoryListCreateAPIView.as_view()),
    path(
        "portfolio/category/<int:pk>/",
        PortfolioCategoryRetrieveUpdateDestroyAPIView.as_view(),
    ),
    path("portfolio/", PortfolioListCreateAPIView.as_view()),
    path("portfolio/<slug:slug>/", PortfolioRetrieveUpdateDestroyAPIView.as_view()),
    path("portfolio/tags/", PortfolioTagsListCreateAPIView.as_view()),
    path(
        "portfolio/tags/<int:pk>/", PortfolioTagsRetrieveUpdateDestroyAPIView.as_view()
    ),
]
