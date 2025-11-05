# pricing/urls.py
from django.urls import path

from .views import PricingListView, TenantUpgradePlanView

urlpatterns = [
    path("plans/", PricingListView.as_view(), name="pricing-list"),
    path("upgrade/", TenantUpgradePlanView.as_view(), name="tenant-upgrade"),
]
