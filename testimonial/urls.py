from django.urls import path
from .views import TestimonialListCreateView, TestimonialRetrieveUpdateDestroyView

urlpatterns = [
    path('testimonial/', TestimonialListCreateView.as_view(),
         name='testimonial-list-create'),
    path('testimonial/<int:pk>/', TestimonialRetrieveUpdateDestroyView.as_view(),
         name='testimonial-retrieve-update-destroy'),
]
