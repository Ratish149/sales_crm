import boto3
from django.conf import settings
from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from blog.views import CustomPagination
from sales_crm.authentication import TenantJWTAuthentication

from .models import Gallery
from .serializers import GallerySerializer, MultipleGalleryUploadSerializer


class GalleryListCreateView(generics.ListCreateAPIView):
    queryset = Gallery.objects.all().order_by("-created_at")
    serializer_class = GallerySerializer
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated]
    authentication_classes = [TenantJWTAuthentication]
    pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.request.method == "POST":
            return MultipleGalleryUploadSerializer
        return super().get_serializer_class()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            images = serializer.validated_data["files"]
            created_instances = []

            for image in images:
                gallery = Gallery.objects.create(image=image)
                created_instances.append(gallery)

            response_serializer = GallerySerializer(created_instances, many=True)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GalleryRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Gallery.objects.all()
    serializer_class = GallerySerializer
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated]
    authentication_classes = [TenantJWTAuthentication]

    def perform_destroy(self, instance):
        # Extract the S3 key from the URL and delete the object
        if instance.image:
            url = instance.image.url
            key = None

            if settings.AWS_S3_CUSTOM_DOMAIN:
                prefix = f"https://{settings.AWS_S3_CUSTOM_DOMAIN}/"
            else:
                prefix = f"{settings.AWS_S3_ENDPOINT_URL}/{settings.AWS_STORAGE_BUCKET_NAME}/"

            if url.startswith(prefix):
                key = url[len(prefix) :]

            if key:
                s3 = boto3.client(
                    "s3",
                    endpoint_url=settings.AWS_S3_ENDPOINT_URL,
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                )
                try:
                    s3.delete_object(
                        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                        Key=key,
                    )
                except Exception as e:
                    # Ignore deletion errors if the file doesn't exist on S3
                    print(f"Error deleting file from S3: {e}")

        # Delete the database record
        instance.delete()
