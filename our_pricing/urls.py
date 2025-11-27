from django.urls import path

from .views import OurPricingListCreateAPIView, OurPricingRetrieveUpdateDestroyAPIView

urlpatterns = [
    path(
        "our-pricing/",
        OurPricingListCreateAPIView.as_view(),
        name="our-pricing-list-create",
    ),
    path(
        "our-pricing/<int:pk>/",
        OurPricingRetrieveUpdateDestroyAPIView.as_view(),
        name="our-pricing-detail",
    ),
]
