from django.urls import path

from .views import MSClarityListCreateView, MSClarityRetrieveUpdateDestroyView

urlpatterns = [
    path(
        "ms-clarity/",
        MSClarityListCreateView.as_view(),
        name="ms-clarity-list-create",
    ),
    path(
        "ms-clarity/<int:pk>/",
        MSClarityRetrieveUpdateDestroyView.as_view(),
        name="ms-clarity-detail",
    ),
]
