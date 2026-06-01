from django.urls import path

from pasalbiz.views import StorefrontProductListView, StoreListAPIView

urlpatterns = [
    path("stores/", StoreListAPIView.as_view(), name="store-list"),
    path(
        "pasalbiz-products/",
        StorefrontProductListView.as_view(),
        name="storefront-product-list",
    ),
]
