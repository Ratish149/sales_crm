from django.urls import path

from .views import (
    BulkCreateFAQView,
    FAQCategoryListCreateView,
    FAQCategoryRetrieveUpdateDestroyView,
    FAQListCreateView,
    FAQRetrieveUpdateDestroyView,
)

urlpatterns = [
    path(
        "faq-category/",
        FAQCategoryListCreateView.as_view(),
        name="faq-category-list-create",
    ),
    path(
        "faq-category/<int:pk>/",
        FAQCategoryRetrieveUpdateDestroyView.as_view(),
        name="faq-category-retrieve-update-destroy",
    ),
    path("faq-bulk-create/", BulkCreateFAQView.as_view(), name="faq-bulk-create"),
    path("faq/", FAQListCreateView.as_view(), name="faq-list-create"),
    path(
        "faq/<int:pk>/",
        FAQRetrieveUpdateDestroyView.as_view(),
        name="faq-retrieve-update-destroy",
    ),
]
