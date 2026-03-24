from django.urls import path
from .views import S3UploadView, S3DeleteView, S3ListView, S3DeleteFolderView

urlpatterns = [
    path('upload/', S3UploadView.as_view(), name='s3-upload'),
    path('delete/', S3DeleteView.as_view(), name='s3-delete'),
    path('files/', S3ListView.as_view(), name='s3-list'),
    path('delete-folder/', S3DeleteFolderView.as_view(), name='s3-delete-folder'),
]
