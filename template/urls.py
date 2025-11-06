from django.urls import path

from .views import (
    FooterRetrieveUpdateDestroyView,
    FooterView,
    NavbarRetrieveUpdateDestroyView,
    NavbarView,
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
        "templates/<slug:slug>/",
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
        "template-pages/<slug:template_slug>/<slug:page_slug>/",
        TemplatePageRetrieveUpdateDestroyView.as_view(),
        name="template-page-detail",
    ),
    # TemplatePageComponent endpoints
    path(
        "template-pages/<slug:template_slug>/<slug:page_slug>/components/",
        TemplatePageComponentListCreateView.as_view(),
        name="template-page-component-list-create",
    ),
    path(
        "template-pages/<slug:template_slug>/<slug:page_slug>/components/<int:component_id>/",
        TemplatePageComponentRetrieveUpdateDestroyView.as_view(),
        name="component-detail",
    ),
    # Navbar endpoints
    path(
        "template-pages/<slug:template_slug>/navbar/",
        NavbarView.as_view(),
        name="navbar",
    ),
    path(
        "template-pages/<slug:template_slug>/navbar/<int:component_id>/",
        NavbarRetrieveUpdateDestroyView.as_view(),
        name="navbar-detail",
    ),
    # Footer endpoints
    path(
        "template-pages/<slug:template_slug>/footer/",
        FooterView.as_view(),
        name="footer",
    ),
    path(
        "template-pages/<slug:template_slug>/footer/<int:component_id>/",
        FooterRetrieveUpdateDestroyView.as_view(),
        name="footer-detail",
    ),
]
