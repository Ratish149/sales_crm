from django.urls import path

from .views import (
    BulkCreateTestimonialView,
    TestimonialListCreateView,
    TestimonialRetrieveUpdateDestroyView,
)

urlpatterns = [
    path(
        "testimonial/",
        TestimonialListCreateView.as_view(),
        name="testimonial-list-create",
    ),
    path(
        "testimonial/<int:pk>/",
        TestimonialRetrieveUpdateDestroyView.as_view(),
        name="testimonial-retrieve-update-destroy",
    ),
    path(
        "testimonial-bulk-create/",
        BulkCreateTestimonialView.as_view(),
        name="testimonial-bulk-create",
    ),
]
