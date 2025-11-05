from django.urls import path
from .views import (
    TemplateListCreateView,
    TemplateRetrieveUpdateDestroyView,
    TemplatePageListCreateView,
    TemplatePageRetrieveUpdateDestroyView,
    TemplatePageComponentListCreateView,
    TemplatePageComponentRetrieveUpdateDestroyView,
)

urlpatterns = [
    # Template endpoints
    path("templates/", TemplateListCreateView.as_view(), name="template-list-create"),
    path(
        "templates/<int:pk>/",
        TemplateRetrieveUpdateDestroyView.as_view(),
        name="template-detail",
    ),
    # TemplatePage endpoints
    path("pages/", TemplatePageListCreateView.as_view(), name="page-list-create"),
    path(
        "pages/<int:id>/",
        TemplatePageRetrieveUpdateDestroyView.as_view(),
        name="page-detail",
    ),
    # TemplatePageComponent endpoints
    path(
        "pages/<int:page_id>/components/",
        TemplatePageComponentListCreateView.as_view(),
        name="component-list-create",
    ),
    path(
        "pages/<int:page_id>/components/<int:component_id>/",
        TemplatePageComponentRetrieveUpdateDestroyView.as_view(),
        name="component-detail",
    ),
]
