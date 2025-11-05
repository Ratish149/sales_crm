# pricing/urls.py
from django.urls import path

from .views import PricingListView, TenantUpgradePlanView, UserSubscriptionListView

urlpatterns = [
    path("plans/", PricingListView.as_view(), name="pricing-list"),
    path("upgrade/", TenantUpgradePlanView.as_view(), name="tenant-upgrade"),
    path(
        "user-subscription/",
        UserSubscriptionListView.as_view(),
        name="user-subscription-list",
    ),
]
