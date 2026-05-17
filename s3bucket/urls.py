from django.urls import path

from .views import (
    S3BulkUploadView,
    S3DeleteFolderView,
    S3DeleteView,
    S3ListView,
    S3UploadView,
)

urlpatterns = [
    path("upload/", S3UploadView.as_view(), name="s3-upload"),
    path("bulk-upload/", S3BulkUploadView.as_view(), name="s3-bulk-upload"),
    path("delete/", S3DeleteView.as_view(), name="s3-delete"),
    path("files/", S3ListView.as_view(), name="s3-list"),
    path("delete-folder/", S3DeleteFolderView.as_view(), name="s3-delete-folder"),
]
