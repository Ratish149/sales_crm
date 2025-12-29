import os

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .orchestrator import WebBuilderOrchestrator


class BuildWebsiteView(APIView):
    """
    API View to trigger the AI Website Builder.
    """

    def post(self, request):
        prompt = request.data.get("prompt")
        tenant_name = request.data.get("tenant_name")
        auto_apply = request.data.get(
            "auto_apply", True
        )  # Default to True - always write files

        if not prompt or not tenant_name:
            return Response(
                {"error": "Prompt and tenant_name are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Construct project path based on tenant
        # Assuming tenants are in media/workspaces/[tenant_name]
        project_root = os.path.join(settings.MEDIA_ROOT, "workspaces", tenant_name)

        if not os.path.exists(project_root):
            return Response(
                {
                    "error": f"Workspace for tenant '{tenant_name}' not found at {project_root}"
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            # Initialize Orchestrator
            orchestrator = WebBuilderOrchestrator(
                project_root=project_root, tenant_name=tenant_name
            )

            # Run Build with auto_apply option
            result = orchestrator.build(user_prompt=prompt, auto_apply=auto_apply)

            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            import traceback

            traceback.print_exc()
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
