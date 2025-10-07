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
    path(
        "portfolio/category/",
        PortfolioCategoryListCreateAPIView.as_view(),
        name="portfolio_category_list_create",
    ),
    path(
        "portfolio/category/<int:pk>/",
        PortfolioCategoryRetrieveUpdateDestroyAPIView.as_view(),
        name="portfolio_category_retrieve_update_destroy",
    ),
    path(
        "portfolio/", PortfolioListCreateAPIView.as_view(), name="portfolio_list_create"
    ),
    path(
        "portfolio/<slug:slug>/",
        PortfolioRetrieveUpdateDestroyAPIView.as_view(),
        name="portfolio_retrieve_update_destroy",
    ),
    path(
        "portfolio/tags/",
        PortfolioTagsListCreateAPIView.as_view(),
        name="portfolio_tags_list_create",
    ),
    path(
        "portfolio/tags/<int:pk>/",
        PortfolioTagsRetrieveUpdateDestroyAPIView.as_view(),
        name="portfolio_tags_retrieve_update_destroy",
    ),
]
