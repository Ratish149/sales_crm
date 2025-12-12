from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import RunnerService


class StartProjectView(APIView):
    def post(self, request):
        workspace_id = request.data.get("workspace_id")
        if not workspace_id:
            return Response(
                {"error": "workspace_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            runner = RunnerService(workspace_id)
            url = runner.run_project()
            return Response({"url": url, "status": "running"})
        except FileNotFoundError:
            return Response(
                {"error": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class StopProjectView(APIView):
    def post(self, request):
        workspace_id = request.data.get("workspace_id")
        if not workspace_id:
            return Response(
                {"error": "workspace_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        runner = RunnerService(workspace_id)
        success, message = runner.stop_project()

        if success:
            return Response({"status": "stopped", "message": message})
        else:
            return Response(
                {"error": message},
                status=status.HTTP_400_BAD_REQUEST
                if message == "Project not running"
                else status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
