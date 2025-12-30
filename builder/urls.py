from django.urls import path

from .views import (
    BuilderIDEView,
    TenantImageAPIView,
    TenantImageListAPIView,
    TenantImageMapUpdateAPIView,
    TenantImageUploadAPIView,
    UpdateTenantJsonAPIView,
)

urlpatterns = [
    path("", BuilderIDEView.as_view(), name="builder_ide"),
    path(
        "media/<str:tenant>/<path:image_path>",
        TenantImageAPIView.as_view(),
        name="tenant_image",
    ),
    path(
        "images-map/<str:tenant>/",
        TenantImageListAPIView.as_view(),
        name="tenant_image_list",
    ),
    path(
        "update-image-map/<str:tenant>/",
        TenantImageMapUpdateAPIView.as_view(),
        name="tenant_image_map_update",
    ),
    path(
        "upload-image/<str:tenant>/",
        TenantImageUploadAPIView.as_view(),
        name="tenant_image_upload",
    ),
    path(
        "use-data/",
        UpdateTenantJsonAPIView.as_view(),
        name="update_tenant_json",
    ),
]
