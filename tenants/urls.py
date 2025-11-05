from django.urls import path

from .views import DomainDetailView, DomainView, FacebookWebhookAPIView

urlpatterns = [
    path("domains/", DomainView.as_view(), name="domain-list"),
    path("domains/<int:pk>/", DomainDetailView.as_view(), name="domain-detail"),
    path(
        "facebook-webhook/", FacebookWebhookAPIView.as_view(), name="facebook_webhook"
    ),
]
