from django.urls import path

from .views import (
    ChangePasswordView,
    CustomerDetailView,
    CustomerLoginView,
    CustomerRegisterView,
    CustomerRequestPasswordResetView,
    CustomerResetPasswordConfirmView,
    CustomerRetrieveUpdateDestroyView,
)

urlpatterns = [
    path(
        "customer/register/", CustomerRegisterView.as_view(), name="customer-register"
    ),
    path("customer/login/", CustomerLoginView.as_view(), name="customer-login"),
    path(
        "customer/change-password/",
        ChangePasswordView.as_view(),
        name="customer-change-password",
    ),
    path(
        "customer/<int:pk>",
        CustomerRetrieveUpdateDestroyView.as_view(),
        name="customer-retrieve-update-destroy",
    ),
    path("customer/detail/", CustomerDetailView.as_view(), name="customer-detail"),
    path(
        "customer/password/reset/",
        CustomerRequestPasswordResetView.as_view(),
        name="customer-password-reset-request",
    ),
    path(
        "customer/password/reset/confirm/",
        CustomerResetPasswordConfirmView.as_view(),
        name="customer-password-reset-confirm",
    ),
]
