import json
import mimetypes
import os
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from django.shortcuts import render
from django.views.generic import TemplateView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class BuilderIDEView(TemplateView):
    template_name = "builder/ide.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if hasattr(self.request, "tenant"):
            context["workspace_id"] = self.request.tenant.schema_name
            context["repo_url"] = getattr(self.request.tenant, "repo_url", "")
        else:
            context["workspace_id"] = "public"
            context["repo_url"] = ""
        return context


class TenantImageAPIView(APIView):
    """
    API to fetch images from the tenant's public folder.
    URL: /api/builder/media/<tenant>/<path:image_path>
    Example: /api/builder/media/tenant1/logo.png
    """

    authentication_classes = []  # Public access, or add authentication if needed
    permission_classes = []  # Public access, or add permissions if needed

    def get(self, request, tenant, image_path):
        try:
            # Construct the base path for the tenant's public folder
            base_path = settings.MEDIA_ROOT / "workspaces" / str(tenant) / "public"

            # Clean the image_path to prevent path traversal attacks
            clean_path = str(image_path).lstrip("/\\")
            full_path = (base_path / clean_path).resolve()

            # Security check: ensure the resolved path is within the tenant's public folder
            if not str(full_path).startswith(str(base_path.resolve())):
                return Response(
                    {"error": "Access denied: Invalid path"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Check if file exists and is a file (not a directory)
            if not full_path.exists() or not full_path.is_file():
                raise Http404("Image not found")

            # Detect the MIME type
            content_type, _ = mimetypes.guess_type(str(full_path))
            if content_type is None:
                content_type = "application/octet-stream"

            # Return the file as a response
            return FileResponse(open(full_path, "rb"), content_type=content_type)

        except Exception as e:
            return Response(
                {"error": f"Failed to retrieve image: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TenantImageListAPIView(APIView):
    """
    API to list all files in the tenant's public folder.
    URL: /api/builder/media/<tenant>/images-map
    Returns: {"filename": "/builder/media/<tenant>/<filename>"}
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request, tenant):
        try:
            public_path = settings.MEDIA_ROOT / "workspaces" / str(tenant) / "public"

            if not public_path.exists():
                return Response({})

            response_data = {}

            # Walk through the directory
            for root, dirs, files in os.walk(public_path):
                for file in files:
                    # Get relative path from public folder
                    full_path = Path(root) / file
                    rel_path = full_path.relative_to(public_path)

                    # Convert to string and ensure forward slashes
                    rel_path_str = str(rel_path).replace("\\", "/")

                    # Construct URL
                    url = f"/media/workspaces/{tenant}/public/{rel_path_str}"

                    # Store in response
                    # Using relative path as key
                    response_data[rel_path_str] = url

            return Response(response_data)

        except Exception as e:
            return Response(
                {"error": f"Failed to list images: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TenantImageMapUpdateAPIView(APIView):
    """
    API to update images.json mapping.
    URL: /api/builder/update-image-map/<tenant>/
    Method: POST
    Body: {"key": "hero", "image": "/filename"}
    """

    authentication_classes = []
    permission_classes = []

    def post(self, request, tenant):
        try:
            key = request.data.get("key")
            value = request.data.get("image")

            if not key or not value:
                return Response(
                    {"error": "Missing 'path' or 'image' in request body"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            workspace_path = settings.MEDIA_ROOT / "workspaces" / str(tenant)
            # Ensure workspace directory exists
            workspace_path.mkdir(parents=True, exist_ok=True)

            images_json_path = workspace_path / "images.json"

            data = {}
            if images_json_path.exists():
                import json

                try:
                    with open(images_json_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    data = {}

            # Update the mapping
            data[key] = f"/{value}"

            import json

            with open(images_json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)

            try:
                # Broadcast update via WebSocket
                from asgiref.sync import async_to_sync
                from channels.layers import get_channel_layer

                from .file_service import FileService

                channel_layer = get_channel_layer()
                file_service = FileService(tenant)
                tree = file_service.generate_tree()

                async_to_sync(channel_layer.group_send)(
                    f"workspace_{tenant}",
                    {
                        "type": "image_map_updated_event",
                        "tree": tree,
                        "data": data,
                    },
                )
            except Exception as e:
                print(f"Failed to broadcast websocket message: {e}")

            return Response(
                {"message": "Image map updated successfully", "updated_map": data},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"error": f"Failed to update image map: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TenantImageUploadAPIView(APIView):
    """
    API to upload an image to the tenant's public folder.
    URL: /api/builder/upload-image/<tenant>/
    Method: POST
    Body: multipart/form-data (key="image")
    Returns: Updated list of all images {"filename": "url"}
    """

    authentication_classes = []
    permission_classes = []
    # parser_classes = [MultiPartParser, FormParser] # Optional: Explicitly set parsers if needed, default usually works

    def post(self, request, tenant):
        try:
            if "image" not in request.FILES:
                return Response(
                    {"error": "No image provided"}, status=status.HTTP_400_BAD_REQUEST
                )

            image_file = request.FILES["image"]

            # Define destination path
            public_path = settings.MEDIA_ROOT / "workspaces" / str(tenant) / "public"
            public_path.mkdir(parents=True, exist_ok=True)

            # Save the file
            file_path = public_path / image_file.name

            # Write file chunks
            with open(file_path, "wb+") as destination:
                for chunk in image_file.chunks():
                    destination.write(chunk)

            # Broadcast WebSocket event
            try:
                from asgiref.sync import async_to_sync
                from channels.layers import get_channel_layer

                from .file_service import FileService

                channel_layer = get_channel_layer()
                file_service = FileService(tenant)
                tree = file_service.generate_tree()

                # Relative path for the event
                rel_file_path = f"public/{image_file.name}"

                async_to_sync(channel_layer.group_send)(
                    f"workspace_{tenant}",
                    {
                        "type": "file_created_event",
                        "path": rel_file_path,
                        "tree": tree,
                        "sender_channel_name": None,  # System triggered
                    },
                )
            except Exception as e:
                print(f"Failed to broadcast websocket message: {e}")

            # Generate updated list of images (Logic reused from TenantImageListAPIView)
            response_data = {}
            if public_path.exists():
                for root, dirs, files in os.walk(public_path):
                    for file in files:
                        full_path = Path(root) / file
                        rel_path = full_path.relative_to(public_path)
                        rel_path_str = str(rel_path).replace("\\", "/")
                        url = f"/media/workspaces/{tenant}/public/{rel_path_str}"
                        response_data[rel_path_str] = url

            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {"error": f"Failed to upload image: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UpdateTenantJsonAPIView(APIView):
    """
    API to update the tenantName in tenant.json file.
    URL: /api/builder/use-data/
    Method: POST
    Body: {}
    Requires: JWT authentication with schema_name in token
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user = request.user
            # Access the Client model via the reverse OneToOne relationship 'client'
            # This assumes the user is the owner of the client
            client = getattr(user, "client", None)

            if not client:
                return Response(
                    {"error": "User is not associated with any tenant/client"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # The display name of the tenant
            new_tenant_name = client.name
            # The schema name (folder name)
            schema_name = client.schema_name

            print("new_tenant_name", new_tenant_name)
            print("schema_name", schema_name)

            # Path to tenant.json file
            # Use schema_name for the folder path, as that is the unique identifier
            tenant_json_path = (
                settings.MEDIA_ROOT / "workspaces" / str(schema_name) / "tenant.json"
            )
            print("tenant_json_path", tenant_json_path)

            if not tenant_json_path.exists():
                return Response(
                    {"error": "tenant.json file not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Read the current JSON content
            with open(tenant_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Update the tenantName field
            old_tenant_name = data.get("tenantName")
            data["tenantName"] = new_tenant_name

            # Write back the updated content
            with open(tenant_json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)

            # Broadcast update via WebSocket
            try:
                from asgiref.sync import async_to_sync
                from channels.layers import get_channel_layer

                from .file_service import FileService

                channel_layer = get_channel_layer()
                file_service = FileService(schema_name)
                tree = file_service.generate_tree()

                async_to_sync(channel_layer.group_send)(
                    f"workspace_{schema_name}",
                    {
                        "type": "file_updated_event",
                        "path": "tenant.json",
                        "content": json.dumps(data, indent=4),
                        "tree": tree,
                    },
                )
            except Exception as e:
                print(f"Failed to broadcast websocket message: {e}")

            return Response(
                {
                    "message": "Tenant name updated successfully in tenant.json",
                    "old_tenant_name": old_tenant_name,
                    "new_tenant_name": new_tenant_name,
                    "current_tenant": schema_name,
                },
                status=status.HTTP_200_OK,
            )

        except json.JSONDecodeError:
            return Response(
                {"error": "Invalid JSON format in tenant.json file"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to update tenant name in tenant.json: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# simple view function backup
def builder_ide(request):
    return render(request, "builder/ide.html")
