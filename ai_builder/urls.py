"""
AI Builder URL Configuration
"""

from django.urls import path

from .views import (
    APIKeyDetailView,
    APIKeyListCreateView,
    HealthCheckView,
    RunAIBuilderView,
)

urlpatterns = [
    path("run/", RunAIBuilderView.as_view(), name="ai_builder_run"),
    path("health/", HealthCheckView.as_view(), name="ai_builder_health"),
    path("apikeys/", APIKeyListCreateView.as_view(), name="apikey_list_create"),
    path("apikeys/<int:pk>/", APIKeyDetailView.as_view(), name="apikey_detail"),
]
