from rest_framework.views import exception_handler
from typing import Optional, Dict, Any
from rest_framework.response import Response
from rest_framework import status


class ErrorResponse:
    def __init__(
        self,
        status_code: int,
        message: str,
        code: Optional[int] = None,
        params: Optional[Dict[str, Any]] = None
    ):
        self.status_code = status_code
        self.message = message
        self.code = code or status_code  # Default to status_code if code not provided
        self.params = params or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status_code,
            "errors": {
                "message": self.message,
                "code": self.code,  # Now using status code as the error code
                "params": self.params
            }
        }

    def to_response(self) -> Response:
        return Response(
            self.to_dict(),
            status=self.status_code
        )


def handle_error(
    status_code: int,
    message: str,
    code: Optional[int] = None,
    params: Optional[Dict[str, Any]] = None
) -> Response:
    """
    Helper function to create a consistent error response
    """
    error = ErrorResponse(status_code, message, code, params)
    return error.to_response()


# Common error responses
def bad_request(message: str, code: int = status.HTTP_400_BAD_REQUEST, params: Optional[Dict] = None) -> Response:
    return handle_error(
        status_code=status.HTTP_400_BAD_REQUEST,
        message=message,
        code=code,
        params=params
    )


def not_found(message: str = "Resource not found", code: int = status.HTTP_404_NOT_FOUND) -> Response:
    return handle_error(
        status_code=status.HTTP_404_NOT_FOUND,
        message=message,
        code=code
    )


def permission_denied(message: str = "Permission denied", code: int = status.HTTP_403_FORBIDDEN) -> Response:
    return handle_error(
        status_code=status.HTTP_403_FORBIDDEN,
        message=message,
        code=code
    )


def server_error(message: str = "Internal server error", code: int = status.HTTP_500_INTERNAL_SERVER_ERROR) -> Response:
    return handle_error(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message=message,
        code=code
    )


def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        # Get the error message from the response
        error_message = None
        if hasattr(exc, 'detail'):
            error_message = str(exc.detail)
        else:
            error_message = str(exc)

        # Create a consistent error response
        error = ErrorResponse(
            status_code=response.status_code,
            message=error_message,
            # Default to status code if no code provided
            code=getattr(exc, 'code', response.status_code),
            params=getattr(exc, 'params', None)
        )

        response.data = error.to_dict()

    return response
