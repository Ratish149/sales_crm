from django.urls import path

from .views import (
    TemplateListCreateView,
    TemplatePageComponentListCreateView,
    TemplatePageComponentRetrieveUpdateDestroyView,
    TemplatePageListCreateView,
    TemplatePageRetrieveUpdateDestroyView,
    TemplateRetrieveUpdateDestroyView,
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
    path(
        "template-pages/",
        TemplatePageListCreateView.as_view(),
        name="template-page-list-create",
    ),
    path(
        "template-pages/<int:id>/",
        TemplatePageRetrieveUpdateDestroyView.as_view(),
        name="template-page-detail",
    ),
    # TemplatePageComponent endpoints
    path(
        "template-pages/<int:page_id>/components/",
        TemplatePageComponentListCreateView.as_view(),
        name="template-page-component-list-create",
    ),
    path(
        "template-pages/<int:page_id>/components/<int:component_id>/",
        TemplatePageComponentRetrieveUpdateDestroyView.as_view(),
        name="component-detail",
    ),
]
