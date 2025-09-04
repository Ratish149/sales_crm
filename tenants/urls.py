from django.urls import path
from .views import DomainView, DomainDetailView

urlpatterns = [
    path('domains/', DomainView.as_view(), name='domain-list'),
    path('domains/<int:pk>/', DomainDetailView.as_view(), name='domain-detail'),
]
