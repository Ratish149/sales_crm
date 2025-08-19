from rest_framework.views import exception_handler
from typing import Optional, Dict, Any, Tuple, Type, Union
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError
from rest_framework.exceptions import APIException

# Error Code Constants


class ErrorCode:
    # 4xx Client Errors
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    VALIDATION_ERROR = 422
    DUPLICATE_ENTRY = 409

    # 5xx Server Errors
    INTERNAL_SERVER_ERROR = 500
    SERVICE_UNAVAILABLE = 503

# Error Message Constants


class ErrorMessage:
    # 4xx Messages
    BAD_REQUEST = "Invalid request"
    UNAUTHORIZED = "Authentication credentials were not provided"
    FORBIDDEN = "You do not have permission to perform this action"
    NOT_FOUND = "The requested resource was not found"
    VALIDATION_ERROR = "Validation error occurred"
    DUPLICATE_ENTRY = "A record with this data already exists"

    # 5xx Messages
    INTERNAL_SERVER_ERROR = "An unexpected error occurred"
    SERVICE_UNAVAILABLE = "Service temporarily unavailable"


# Error Type to Code/Message Mapping
ERROR_MAPPING = {
    ValidationError: (status.HTTP_400_BAD_REQUEST, ErrorCode.VALIDATION_ERROR, ErrorMessage.VALIDATION_ERROR),
    APIException: (status.HTTP_400_BAD_REQUEST, ErrorCode.BAD_REQUEST, ErrorMessage.BAD_REQUEST),
    Exception: (status.HTTP_500_INTERNAL_SERVER_ERROR,
                ErrorCode.INTERNAL_SERVER_ERROR, ErrorMessage.INTERNAL_SERVER_ERROR)
}


def get_error_details(exception: Exception) -> Tuple[int, int, str, Dict[str, Any]]:
    """
    Get standardized error details from an exception
    Returns: (http_status_code, error_code, error_message, error_params)
    """
    error_params = {}

    # Handle Django ValidationError
    if isinstance(exception, ValidationError):
        error_params = getattr(exception, 'params', {})
        if hasattr(exception, 'message_dict'):
            error_params['errors'] = exception.message_dict
        return (status.HTTP_400_BAD_REQUEST,
                ErrorCode.VALIDATION_ERROR,
                str(exception) or ErrorMessage.VALIDATION_ERROR,
                error_params)

    # Handle DRF APIException
    if isinstance(exception, APIException):
        status_code = exception.status_code
        error_code = getattr(exception, 'code', ErrorCode.BAD_REQUEST)
        error_message = str(exception.detail) if hasattr(
            exception, 'detail') else str(exception)
        return (status_code, error_code, error_message, error_params)

    # Default to internal server error
    return (status.HTTP_500_INTERNAL_SERVER_ERROR,
            ErrorCode.INTERNAL_SERVER_ERROR,
            ErrorMessage.INTERNAL_SERVER_ERROR,
            error_params)


class ErrorResponse:
    """
    Standardized error response format for the API

    Example:
        {
            "status": 400,
            "error": {
                "code": 400,
                "message": "Detailed error message",
                "params": {
                    "field_name": "Error details"
                }
            }
        }
    """

    def __init__(
        self,
        status_code: int,
        message: str,
        code: Optional[int] = None,
        params: Optional[Dict[str, Any]] = None
    ):
        self.status_code = status_code
        self.message = message
        self.code = code or ErrorCode.INTERNAL_SERVER_ERROR
        self.params = params or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert the error response to a dictionary format"""
        return {
            "status": self.status_code,
            "error": {
                "code": self.code,
                "message": self.message,
                "params": self.params
            }
        }

    def to_response(self) -> Response:
        """Convert the error response to a DRF Response object"""
        return Response(
            self.to_dict(),
            status=self.status_code
        )

    @classmethod
    def from_exception(cls, exc: Exception) -> 'ErrorResponse':
        """Create an ErrorResponse from an exception"""
        status_code, error_code, message, params = get_error_details(exc)
        return cls(
            status_code=status_code,
            message=message,
            code=error_code,
            params=params
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


def bad_request(message: str = ErrorMessage.BAD_REQUEST,
                code: int = ErrorCode.BAD_REQUEST,
                params: Optional[Dict] = None) -> Response:
    """400 Bad Request"""
    return handle_error(
        status_code=status.HTTP_400_BAD_REQUEST,
        message=message,
        code=code,
        params=params
    )


def unauthorized(message: str = ErrorMessage.UNAUTHORIZED,
                 code: int = ErrorCode.UNAUTHORIZED,
                 params: Optional[Dict] = None) -> Response:
    """401 Unauthorized"""
    return handle_error(
        status_code=status.HTTP_401_UNAUTHORIZED,
        message=message,
        code=code,
        params=params
    )


def forbidden(message: str = ErrorMessage.FORBIDDEN,
              code: int = ErrorCode.FORBIDDEN,
              params: Optional[Dict] = None) -> Response:
    """403 Forbidden"""
    return handle_error(
        status_code=status.HTTP_403_FORBIDDEN,
        message=message,
        code=code,
        params=params
    )


def not_found(message: str = ErrorMessage.NOT_FOUND,
              code: int = ErrorCode.NOT_FOUND,
              params: Optional[Dict] = None) -> Response:
    """404 Not Found"""
    return handle_error(
        status_code=status.HTTP_404_NOT_FOUND,
        message=message,
        code=code,
        params=params
    )


def validation_error(message: str = ErrorMessage.VALIDATION_ERROR,
                     code: int = ErrorCode.VALIDATION_ERROR,
                     params: Optional[Dict] = None) -> Response:
    """422 Unprocessable Entity"""
    return handle_error(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message=message,
        code=code,
        params=params
    )


def duplicate_entry(message: str = ErrorMessage.DUPLICATE_ENTRY,
                    code: int = ErrorCode.DUPLICATE_ENTRY,
                    params: Optional[Dict] = None) -> Response:
    """409 Conflict - Duplicate Entry"""
    return handle_error(
        status_code=status.HTTP_409_CONFLICT,
        message=message,
        code=code,
        params=params
    )


def server_error(message: str = ErrorMessage.INTERNAL_SERVER_ERROR,
                 code: int = ErrorCode.INTERNAL_SERVER_ERROR,
                 params: Optional[Dict] = None) -> Response:
    """500 Internal Server Error"""
    return handle_error(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message=message,
        code=code,
        params=params
    )


def service_unavailable(message: str = ErrorMessage.SERVICE_UNAVAILABLE,
                        code: int = ErrorCode.SERVICE_UNAVAILABLE,
                        params: Optional[Dict] = None) -> Response:
    """503 Service Unavailable"""
    return handle_error(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        message=message,
        code=code,
        params=params
    )


def custom_exception_handler(exc: Exception, context: Dict[str, Any]) -> Response:
    """
    Custom exception handler that returns consistent error responses.
    Handles both Django and DRF exceptions.
    """
    # Get the response from the default exception handler
    response = exception_handler(exc, context)

    if response is None:
        # For unhandled exceptions, return a 500 response
        error = ErrorResponse.from_exception(exc)
        response = error.to_response()
    else:
        # For handled exceptions, format the response consistently
        status_code = response.status_code

        # Get error details from the exception
        error_code = getattr(exc, 'code', None)
        error_message = str(exc.detail) if hasattr(exc, 'detail') else str(exc)
        error_params = getattr(exc, 'params', {})

        # Map status code to default error code if not provided
        if error_code is None:
            if status_code == status.HTTP_400_BAD_REQUEST:
                error_code = ErrorCode.BAD_REQUEST
            elif status_code == status.HTTP_401_UNAUTHORIZED:
                error_code = ErrorCode.UNAUTHORIZED
            elif status_code == status.HTTP_403_FORBIDDEN:
                error_code = ErrorCode.FORBIDDEN
            elif status_code == status.HTTP_404_NOT_FOUND:
                error_code = ErrorCode.NOT_FOUND
            elif status_code == status.HTTP_409_CONFLICT:
                error_code = ErrorCode.DUPLICATE_ENTRY
            elif status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
                error_code = ErrorCode.VALIDATION_ERROR
            else:
                error_code = ErrorCode.INTERNAL_SERVER_ERROR

        # Create the error response
        error = ErrorResponse(
            status_code=status_code,
            message=error_message,
            code=error_code,
            params=error_params
        )

        response.data = error.to_dict()

    return response
