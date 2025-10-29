from django.urls import path

from .views import (
    PromoCodeListCreateView,
    PromoCodeRetrieveUpdateDestroyView,
    validate_promo_code,
)

urlpatterns = [
    path(
        "promocode/", PromoCodeListCreateView.as_view(), name="promo-code-list-create"
    ),
    path(
        "promocode/<int:pk>",
        PromoCodeRetrieveUpdateDestroyView.as_view(),
        name="promo-code-retrieve-update-destroy",
    ),
    path(
        "promocode/validate/",
        validate_promo_code,
        name="promo-code-validate",
    ),
]
