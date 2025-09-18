from django.urls import path
from .views import (
    CustomerRegisterView,
    CustomerLoginView,
)

urlpatterns = [
    path("customer/register/", CustomerRegisterView.as_view(),
         name="customer-register"),
    path("customer/login/", CustomerLoginView.as_view(), name="customer-login"),
]
