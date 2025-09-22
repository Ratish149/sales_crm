from django.urls import path

from .views import (
    CategoryListCreateView,
    CategoryRetrieveUpdateDestroyView,
    ProductImageListCreateView,
    ProductImageRetrieveUpdateDestroyView,
    ProductListCreateView,
    ProductRetrieveUpdateDestroyView,
    ProductReviewRetrieveUpdateDestroyView,
    ProductReviewView,
    SubCategoryListCreateView,
    SubCategoryRetrieveUpdateDestroyView,
    WishlistListCreateView,
    WishlistRetrieveUpdateDestroyView,
)

urlpatterns = [
    path("product/", ProductListCreateView.as_view(), name="product-list-create"),
    path(
        "product/<slug:slug>/",
        ProductRetrieveUpdateDestroyView.as_view(),
        name="product-retrieve-update-destroy",
    ),
    path(
        "sub-category/",
        SubCategoryListCreateView.as_view(),
        name="sub-category-list-create",
    ),
    path(
        "sub-category/<slug:slug>/",
        SubCategoryRetrieveUpdateDestroyView.as_view(),
        name="sub-category-retrieve-update-destroy",
    ),
    path("category/", CategoryListCreateView.as_view(), name="category-list-create"),
    path(
        "category/<slug:slug>/",
        CategoryRetrieveUpdateDestroyView.as_view(),
        name="category-retrieve-update-destroy",
    ),
    path(
        "product-image/",
        ProductImageListCreateView.as_view(),
        name="product-image-list-create",
    ),
    path(
        "product-image/<int:pk>/",
        ProductImageRetrieveUpdateDestroyView.as_view(),
        name="product-image-retrieve-update-destroy",
    ),
    path(
        "product-review/",
        ProductReviewView.as_view(),
        name="product-review-list-create",
    ),
    path(
        "product-review/<int:id>/",
        ProductReviewRetrieveUpdateDestroyView.as_view(),
        name="product-review-retrieve-update-destroy",
    ),
    path("wishlist/", WishlistListCreateView.as_view(), name="wishlist-list-create"),
    path(
        "wishlist/<int:id>/",
        WishlistRetrieveUpdateDestroyView.as_view(),
        name="wishlist-retrieve-update-destroy",
    ),
]
