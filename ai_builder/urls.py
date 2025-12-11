"""
AI Builder URL Configuration
"""

from django.urls import path

from .views import HealthCheckView, RunAIBuilderView

urlpatterns = [
    path("run/", RunAIBuilderView.as_view(), name="ai_builder_run"),
    path("health/", HealthCheckView.as_view(), name="ai_builder_health"),
]
