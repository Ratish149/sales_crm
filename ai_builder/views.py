"""
AI Builder Views

DRF views for the AI builder functionality.
"""

import os

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .orchestrator import orchestrate_agent


class RunAIBuilderView(APIView):
    """
    POST /ai-builder/run/

    Runs the AI agent to process a user prompt and modify project files.

    Request body:
    {
        "prompt": "Make the header background blue",
        "project_path": "media/tenant_projects/123"  // Relative to MEDIA_ROOT or absolute
    }

    Response:
    {
        "status": "success",
        "final_answer": "I've updated the header background to blue...",
        "files_modified": ["src/App.css", "src/components/Header.jsx"],
        "iterations": 3,
        "conversation_log": [...]
    }
    """

    def post(self, request):
        # Extract data
        prompt = request.data.get("prompt")
        project_path = request.data.get("project_path")
        print("Project path:", project_path)
        print("Prompt:", prompt)

        # Validate
        if not prompt:
            return Response(
                {"error": "Missing 'prompt' field"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not project_path:
            return Response(
                {"error": "Missing 'project_path' field"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Resolve project path
        # If relative, make it relative to MEDIA_ROOT
        if not os.path.isabs(project_path):
            media_root = settings.MEDIA_ROOT
            project_root = os.path.join(media_root, project_path)
        else:
            project_root = project_path

        # Validate project root exists
        if not os.path.exists(project_root):
            return Response(
                {"error": f"Project path does not exist: {project_root}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Run orchestrator
        try:
            result = orchestrate_agent(
                user_prompt=prompt,
                project_root=project_root,
                max_iterations=request.data.get("max_iterations", 10),
            )

            # Return result
            if result["status"] == "success":
                return Response(result, status=status.HTTP_200_OK)
            elif result["status"] == "partial":
                return Response(result, status=status.HTTP_206_PARTIAL_CONTENT)
            else:
                return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            # Log full traceback for debugging
            import traceback

            error_traceback = traceback.format_exc()
            print(f"AI Builder Error: {str(e)}")
            print(f"Traceback:\n{error_traceback}")

            return Response(
                {
                    "status": "error",
                    "message": str(e),
                    "traceback": error_traceback,  # Include traceback in response for debugging
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class HealthCheckView(APIView):
    """
    GET /ai-builder/health/

    Health check endpoint.
    """

    def get(self, request):
        return Response({"status": "ok", "service": "ai_builder"})
