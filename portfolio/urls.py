from django.urls import path

from .views import (
    PortfolioCategoryListCreateAPIView,
    PortfolioCategoryRetrieveUpdateDestroyAPIView,
    PortfolioImageListCreateAPIView,
    PortfolioImageRetrieveUpdateDestroyAPIView,
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
        "portfolio-tags/",
        PortfolioTagsListCreateAPIView.as_view(),
        name="portfolio_tags_list_create",
    ),
    path(
        "portfolio-tags/<int:pk>/",
        PortfolioTagsRetrieveUpdateDestroyAPIView.as_view(),
        name="portfolio_tags_retrieve_update_destroy",
    ),
    path(
        "portfolio-image/",
        PortfolioImageListCreateAPIView.as_view(),
        name="portfolio_image_list_create",
    ),
    path(
        "portfolio-image/<int:pk>/",
        PortfolioImageRetrieveUpdateDestroyAPIView.as_view(),
        name="portfolio_image_retrieve_update_destroy",
    ),
]
