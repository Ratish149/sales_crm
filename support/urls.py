from django.urls import path

from .views import (
    ContactListCreateView,
    ContactRetrieveUpdateDestroyView,
    FAQCategoryListCreateView,
    FAQCategoryRetrieveUpdateDestroyView,
    FAQListCreateView,
    FAQRetrieveUpdateDestroyView,
    NepdoraTestimonialListCreateView,
    NepdoraTestimonialRetrieveUpdateDestroyView,
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
    path("faq/", FAQListCreateView.as_view(), name="faq-list-create"),
    path(
        "faq/<int:pk>/",
        FAQRetrieveUpdateDestroyView.as_view(),
        name="faq-retrieve-update-destroy",
    ),
    path(
        "nepdora-testimonial/",
        NepdoraTestimonialListCreateView.as_view(),
        name="nepdora-testimonial-list-create",
    ),
    path(
        "nepdora-testimonial/<int:pk>/",
        NepdoraTestimonialRetrieveUpdateDestroyView.as_view(),
        name="nepdora-testimonial-retrieve-update-destroy",
    ),
    path(
        "nepdora-contact/",
        ContactListCreateView.as_view(),
        name="nepdora-contact-list-create",
    ),
    path(
        "nepdora-contact/<int:pk>/",
        ContactRetrieveUpdateDestroyView.as_view(),
        name="nepdora-contact-retrieve-update-destroy",
    ),
]
