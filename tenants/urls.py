from django.urls import path

from .views import (
    ClientTokenByIdAPIView,
    DomainDetailView,
    DomainView,
    FacebookWebhookView,
    TemplateTenantListAPIView,
)

urlpatterns = [
    path("domains/", DomainView.as_view(), name="domain-list"),
    path("domains/<int:pk>/", DomainDetailView.as_view(), name="domain-detail"),
    path("facebook-webhook", FacebookWebhookView.as_view(), name="facebook_webhook"),
    path(
        "template-tenants/",
        TemplateTenantListAPIView.as_view(),
        name="template-tenants-list",
    ),
    path(
        "template-tokens/",
        ClientTokenByIdAPIView.as_view(),
        name="template-token-by-id",
    ),
]
