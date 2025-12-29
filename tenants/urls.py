from django.urls import path

from .views import (
    ClientTokenByIdAPIView,
    DomainDetailView,
    DomainView,
    # FacebookWebhookView,
    TemplateCategoryListCreateView,
    TemplateCategoryRetrieveUpdateDeleteView,
    TemplateSubCategoryListCreateView,
    TemplateSubCategoryRetrieveUpdateDeleteView,
    TemplateTenantListAPIView,
    TemplateTenantRetrieveUpdateDestroyAPIView,
)

urlpatterns = [
    path("domains/", DomainView.as_view(), name="domain-list"),
    path("domains/<int:pk>/", DomainDetailView.as_view(), name="domain-detail"),
    # path("facebook-webhook", FacebookWebhookView.as_view(), name="facebook_webhook"),
    path(
        "template-tenants/",
        TemplateTenantListAPIView.as_view(),
        name="template-tenants-list",
    ),
    path(
        "template-tenants/<int:owner_id>/",
        TemplateTenantRetrieveUpdateDestroyAPIView.as_view(),
        name="template-tenant-detail",
    ),
    path(
        "template-tokens/",
        ClientTokenByIdAPIView.as_view(),
        name="template-token-by-id",
    ),
    path(
        "template-categories/",
        TemplateCategoryListCreateView.as_view(),
        name="category-list-create",
    ),
    path(
        "template-categories/<str:slug>/",
        TemplateCategoryRetrieveUpdateDeleteView.as_view(),
        name="category-detail",
    ),
    # SubCategory
    path(
        "template-subcategories/",
        TemplateSubCategoryListCreateView.as_view(),
        name="subcategory-list-create",
    ),
    path(
        "template-subcategories/<str:slug>/",
        TemplateSubCategoryRetrieveUpdateDeleteView.as_view(),
        name="subcategory-detail",
    ),
]
