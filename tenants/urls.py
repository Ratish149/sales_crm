from django.urls import path

from .views import DomainDetailView, DomainView, FacebookWebhookView

urlpatterns = [
    path("domains/", DomainView.as_view(), name="domain-list"),
    path("domains/<int:pk>/", DomainDetailView.as_view(), name="domain-detail"),
    path("facebook-webhook/", FacebookWebhookView.as_view(), name="facebook_webhook"),
]
