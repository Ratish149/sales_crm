from django.urls import path
from .views import ProductListCreateView, ProductRetrieveUpdateDestroyView, SubCategoryListCreateView, SubCategoryRetrieveUpdateDestroyView, CategoryListCreateView, CategoryRetrieveUpdateDestroyView, ProductImageListCreateView, ProductImageRetrieveUpdateDestroyView

urlpatterns = [
    path('product/', ProductListCreateView.as_view(), name='product-list-create'),
    path('product/<slug:slug>/', ProductRetrieveUpdateDestroyView.as_view(),
         name='product-retrieve-update-destroy'),
    path('sub-category/', SubCategoryListCreateView.as_view(), name='sub-category-list-create'),
    path('sub-category/<slug:slug>/', SubCategoryRetrieveUpdateDestroyView.as_view(),
         name='sub-category-retrieve-update-destroy'),
    path('category/', CategoryListCreateView.as_view(), name='category-list-create'),
    path('category/<slug:slug>/', CategoryRetrieveUpdateDestroyView.as_view(),
         name='category-retrieve-update-destroy'),
    path('product-image/', ProductImageListCreateView.as_view(), name='product-image-list-create'),
    path('product-image/<int:pk>/', ProductImageRetrieveUpdateDestroyView.as_view(),
         name='product-image-retrieve-update-destroy'),
]
