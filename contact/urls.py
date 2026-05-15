from django.urls import path

from .views import (
    ContactCreateView,
    ContactExcelExportView,
    ContactRetrieveUpdateDestroyView,
    NewsLetterCreateView,
    NewsLetterRetrieveUpdateDestroyView,
)

urlpatterns = [
    path("contact/", ContactCreateView.as_view(), name="contact-create"),
    path(
        "contact-export/",
        ContactExcelExportView.as_view(),
        name="contact-export",
    ),
    path(
        "contact/<int:pk>/",
        ContactRetrieveUpdateDestroyView.as_view(),
        name="contact-retrieve-update-destroy",
    ),
    path("newsletter/", NewsLetterCreateView.as_view(), name="newsletter-create"),
    path(
        "newsletter/<int:pk>/",
        NewsLetterRetrieveUpdateDestroyView.as_view(),
        name="newsletter-retrieve-update-destroy",
    ),
]
