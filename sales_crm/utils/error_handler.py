from rest_framework.views import exception_handler
from typing import Optional, Dict, Any, Tuple
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import (
    ValidationError,
    ObjectDoesNotExist,
    MultipleObjectsReturned,
    PermissionDenied,
    SuspiciousOperation,
    ImproperlyConfigured,
    FieldError,
    FieldDoesNotExist
)
from django.db import (
    IntegrityError,
    DatabaseError,
    OperationalError,
    ProgrammingError,
    DataError,
    NotSupportedError,
    InternalError,
    transaction
)
from django.db.models import ProtectedError, RestrictedError
from django.http import Http404
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied as DRFPermissionDenied,
    NotFound,
    ValidationError as DRFValidationError,
    ParseError,
    UnsupportedMediaType,
    Throttled,
    MethodNotAllowed
)
from django.conf import settings
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Error Code Constants


class ErrorCode:
    # 4xx Client Errors
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    NOT_ACCEPTABLE = 406
    DUPLICATE_ENTRY = 409
    VALIDATION_ERROR = 422
    UNSUPPORTED_MEDIA_TYPE = 415
    TOO_MANY_REQUESTS = 429

    # Database specific errors
    FOREIGN_KEY_VIOLATION = 4001
    PROTECTED_ERROR = 4002
    RESTRICTED_ERROR = 4003
    FIELD_ERROR = 4004

    # 5xx Server Errors
    INTERNAL_SERVER_ERROR = 500
    NOT_IMPLEMENTED = 501
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503
    GATEWAY_TIMEOUT = 504

    # Database server errors
    DATABASE_ERROR = 5001
    OPERATIONAL_ERROR = 5002
    PROGRAMMING_ERROR = 5003
    DATA_ERROR = 5004
    INTEGRITY_ERROR = 5005

# Error Message Constants


class ErrorMessage:
    # 4xx Messages
    BAD_REQUEST = "Invalid request"
    UNAUTHORIZED = "Authentication credentials were not provided"
    FORBIDDEN = "You do not have permission to perform this action"
    NOT_FOUND = "The requested resource was not found"
    METHOD_NOT_ALLOWED = "Method not allowed"
    VALIDATION_ERROR = "Validation error occurred"
    DUPLICATE_ENTRY = "A record with this data already exists"
    PARSE_ERROR = "Malformed request data"
    UNSUPPORTED_MEDIA_TYPE = "Unsupported media type"
    THROTTLED = "Request was throttled"

    # Database specific messages
    FOREIGN_KEY_VIOLATION = "Referenced object does not exist"
    PROTECTED_ERROR = "Cannot delete this record because it is referenced by other records"
    RESTRICTED_ERROR = "Cannot delete this record due to restrictions"
    FIELD_ERROR = "Invalid field or query"
    MULTIPLE_OBJECTS_RETURNED = "Multiple objects returned when only one was expected"

    # 5xx Messages
    INTERNAL_SERVER_ERROR = "An unexpected error occurred"
    DATABASE_ERROR = "Database error occurred"
    OPERATIONAL_ERROR = "Database operational error"
    PROGRAMMING_ERROR = "Database programming error"
    DATA_ERROR = "Database data error"
    SERVICE_UNAVAILABLE = "Service temporarily unavailable"


def get_error_details(exception: Exception) -> Tuple[int, int, str, Dict[str, Any]]:
    """
    Get standardized error details from an exception
    Returns: (http_status_code, error_code, error_message, error_params)
    """
    error_params = {}

    # Django Core Exceptions
    if isinstance(exception, ValidationError):
        error_params = getattr(exception, 'params', {})
        if hasattr(exception, 'message_dict'):
            error_params['field_errors'] = exception.message_dict
        elif hasattr(exception, 'messages'):
            error_params['messages'] = exception.messages
        return (
            status.HTTP_400_BAD_REQUEST,
            ErrorCode.VALIDATION_ERROR,
            str(exception) or ErrorMessage.VALIDATION_ERROR,
            error_params
        )

    if isinstance(exception, ObjectDoesNotExist):
        model_name = getattr(exception, 'model', 'Object').__name__ if hasattr(
            exception, 'model') else 'Object'
        error_params['model'] = model_name
        return (
            status.HTTP_404_NOT_FOUND,
            ErrorCode.NOT_FOUND,
            f"{model_name} not found",
            error_params
        )

    if isinstance(exception, MultipleObjectsReturned):
        model_name = getattr(exception, 'model', 'Object').__name__ if hasattr(
            exception, 'model') else 'Object'
        error_params['model'] = model_name
        return (
            status.HTTP_400_BAD_REQUEST,
            ErrorCode.BAD_REQUEST,
            ErrorMessage.MULTIPLE_OBJECTS_RETURNED,
            error_params
        )

    if isinstance(exception, PermissionDenied):
        return (
            status.HTTP_403_FORBIDDEN,
            ErrorCode.FORBIDDEN,
            str(exception) or ErrorMessage.FORBIDDEN,
            error_params
        )

    if isinstance(exception, SuspiciousOperation):
        logger.warning(f"Suspicious operation: {exception}")
        return (
            status.HTTP_400_BAD_REQUEST,
            ErrorCode.BAD_REQUEST,
            "Invalid request detected",
            error_params
        )

    if isinstance(exception, FieldError):
        error_params['field_error'] = str(exception)
        return (
            status.HTTP_400_BAD_REQUEST,
            ErrorCode.FIELD_ERROR,
            ErrorMessage.FIELD_ERROR,
            error_params
        )

    if isinstance(exception, FieldDoesNotExist):
        error_params['field_name'] = getattr(
            exception, 'field_name', 'unknown')
        return (
            status.HTTP_400_BAD_REQUEST,
            ErrorCode.FIELD_ERROR,
            f"Field '{error_params['field_name']}' does not exist",
            error_params
        )

    # Database Exceptions
    if isinstance(exception, IntegrityError):
        error_message = ErrorMessage.DUPLICATE_ENTRY
        exception_str = str(exception).lower()

        if 'unique constraint' in exception_str or 'duplicate key' in exception_str:
            error_params['constraint_type'] = 'unique'
            if 'unique_together' in exception_str or ('(' in exception_str and ')' in exception_str):
                error_message = "This combination of values already exists"
                error_params['constraint'] = 'unique_together'
            else:
                error_message = "This value already exists"
        elif 'foreign key constraint' in exception_str or 'violates foreign key' in exception_str:
            error_params['constraint_type'] = 'foreign_key'
            error_message = ErrorMessage.FOREIGN_KEY_VIOLATION
            return (
                status.HTTP_400_BAD_REQUEST,
                ErrorCode.FOREIGN_KEY_VIOLATION,
                error_message,
                error_params
            )
        elif 'not null constraint' in exception_str or 'null value' in exception_str:
            error_params['constraint_type'] = 'not_null'
            error_message = "Required field cannot be empty"
        elif 'check constraint' in exception_str:
            error_params['constraint_type'] = 'check'
            error_message = "Data violates database constraints"

        return (
            status.HTTP_409_CONFLICT,
            ErrorCode.DUPLICATE_ENTRY,
            error_message,
            error_params
        )

    if isinstance(exception, ProtectedError):
        error_params['protected_objects'] = len(
            exception.protected_objects) if hasattr(exception, 'protected_objects') else 0
        return (
            status.HTTP_400_BAD_REQUEST,
            ErrorCode.PROTECTED_ERROR,
            ErrorMessage.PROTECTED_ERROR,
            error_params
        )

    if isinstance(exception, RestrictedError):
        error_params['restricted_objects'] = len(
            exception.restricted_objects) if hasattr(exception, 'restricted_objects') else 0
        return (
            status.HTTP_400_BAD_REQUEST,
            ErrorCode.RESTRICTED_ERROR,
            ErrorMessage.RESTRICTED_ERROR,
            error_params
        )

    if isinstance(exception, DataError):
        return (
            status.HTTP_400_BAD_REQUEST,
            ErrorCode.DATA_ERROR,
            ErrorMessage.DATA_ERROR,
            error_params
        )

    if isinstance(exception, OperationalError):
        logger.error(f"Database operational error: {exception}")
        return (
            status.HTTP_503_SERVICE_UNAVAILABLE,
            ErrorCode.OPERATIONAL_ERROR,
            ErrorMessage.OPERATIONAL_ERROR,
            error_params
        )

    if isinstance(exception, ProgrammingError):
        logger.error(f"Database programming error: {exception}")
        return (
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            ErrorCode.PROGRAMMING_ERROR,
            ErrorMessage.PROGRAMMING_ERROR,
            error_params
        )

    if isinstance(exception, DatabaseError):
        logger.error(f"Database error: {exception}")
        return (
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            ErrorCode.DATABASE_ERROR,
            ErrorMessage.DATABASE_ERROR,
            error_params
        )

    if isinstance(exception, InternalError):
        logger.error(f"Database internal error: {exception}")
        return (
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            ErrorCode.DATABASE_ERROR,
            "Database internal error occurred",
            error_params
        )

    if isinstance(exception, NotSupportedError):
        return (
            status.HTTP_501_NOT_IMPLEMENTED,
            ErrorCode.NOT_IMPLEMENTED,
            "Operation not supported by database",
            error_params
        )

    # HTTP Exceptions
    if isinstance(exception, Http404):
        return (
            status.HTTP_404_NOT_FOUND,
            ErrorCode.NOT_FOUND,
            ErrorMessage.NOT_FOUND,
            error_params
        )

    # DRF Exceptions
    if isinstance(exception, NotAuthenticated):
        return (
            status.HTTP_401_UNAUTHORIZED,
            ErrorCode.UNAUTHORIZED,
            str(exception) or ErrorMessage.UNAUTHORIZED,
            error_params
        )

    if isinstance(exception, AuthenticationFailed):
        return (
            status.HTTP_401_UNAUTHORIZED,
            ErrorCode.UNAUTHORIZED,
            str(exception) or "Authentication failed",
            error_params
        )

    if isinstance(exception, DRFPermissionDenied):
        return (
            status.HTTP_403_FORBIDDEN,
            ErrorCode.FORBIDDEN,
            str(exception) or ErrorMessage.FORBIDDEN,
            error_params
        )

    if isinstance(exception, NotFound):
        return (
            status.HTTP_404_NOT_FOUND,
            ErrorCode.NOT_FOUND,
            str(exception) or ErrorMessage.NOT_FOUND,
            error_params
        )

    if isinstance(exception, MethodNotAllowed):
        error_params['allowed_methods'] = getattr(
            exception, 'allowed_methods', [])
        return (
            status.HTTP_405_METHOD_NOT_ALLOWED,
            ErrorCode.METHOD_NOT_ALLOWED,
            str(exception) or ErrorMessage.METHOD_NOT_ALLOWED,
            error_params
        )

    if isinstance(exception, ParseError):
        return (
            status.HTTP_400_BAD_REQUEST,
            ErrorCode.BAD_REQUEST,
            str(exception) or ErrorMessage.PARSE_ERROR,
            error_params
        )

    if isinstance(exception, UnsupportedMediaType):
        return (
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            ErrorCode.UNSUPPORTED_MEDIA_TYPE,
            str(exception) or ErrorMessage.UNSUPPORTED_MEDIA_TYPE,
            error_params
        )

    if isinstance(exception, Throttled):
        error_params['wait'] = getattr(exception, 'wait', None)
        return (
            status.HTTP_429_TOO_MANY_REQUESTS,
            ErrorCode.TOO_MANY_REQUESTS,
            str(exception) or ErrorMessage.THROTTLED,
            error_params
        )

    if isinstance(exception, DRFValidationError):
        if hasattr(exception, 'detail'):
            if isinstance(exception.detail, dict):
                error_params['field_errors'] = exception.detail
            elif isinstance(exception.detail, list):
                error_params['errors'] = exception.detail
        return (
            status.HTTP_400_BAD_REQUEST,
            ErrorCode.VALIDATION_ERROR,
            str(exception) or ErrorMessage.VALIDATION_ERROR,
            error_params
        )

    # Generic DRF APIException
    if isinstance(exception, APIException):
        status_code = getattr(exception, 'status_code',
                              status.HTTP_500_INTERNAL_SERVER_ERROR)
        error_code = getattr(
            exception, 'code', ErrorCode.INTERNAL_SERVER_ERROR)
        error_message = str(getattr(exception, 'detail', exception))
        return (status_code, error_code, error_message, error_params)

    # Configuration Errors (should not happen in production)
    if isinstance(exception, ImproperlyConfigured):
        logger.error(f"Configuration error: {exception}")
        return (
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            ErrorCode.INTERNAL_SERVER_ERROR,
            "Server configuration error" if not settings.DEBUG else str(
                exception),
            error_params
        )

    # Default fallback
    logger.error(
        f"Unhandled exception: {type(exception).__name__}: {exception}")
    return (
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        ErrorCode.INTERNAL_SERVER_ERROR,
        ErrorMessage.INTERNAL_SERVER_ERROR,
        error_params
    )


class ErrorResponse:
    """
    Standardized error response format for the API
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
            },
            "success": False
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
    """Helper function to create a consistent error response"""
    error = ErrorResponse(status_code, message, code, params)
    return error.to_response()


# Convenience functions for common errors
def bad_request(message: str = ErrorMessage.BAD_REQUEST, params: Optional[Dict] = None) -> Response:
    """400 Bad Request"""
    return handle_error(status.HTTP_400_BAD_REQUEST, message, ErrorCode.BAD_REQUEST, params)


def unauthorized(message: str = ErrorMessage.UNAUTHORIZED, params: Optional[Dict] = None) -> Response:
    """401 Unauthorized"""
    return handle_error(status.HTTP_401_UNAUTHORIZED, message, ErrorCode.UNAUTHORIZED, params)


def forbidden(message: str = ErrorMessage.FORBIDDEN, params: Optional[Dict] = None) -> Response:
    """403 Forbidden"""
    return handle_error(status.HTTP_403_FORBIDDEN, message, ErrorCode.FORBIDDEN, params)


def not_found(message: str = ErrorMessage.NOT_FOUND, params: Optional[Dict] = None) -> Response:
    """404 Not Found"""
    return handle_error(status.HTTP_404_NOT_FOUND, message, ErrorCode.NOT_FOUND, params)


def validation_error(message: str = ErrorMessage.VALIDATION_ERROR, params: Optional[Dict] = None) -> Response:
    """422 Unprocessable Entity"""
    return handle_error(status.HTTP_422_UNPROCESSABLE_ENTITY, message, ErrorCode.VALIDATION_ERROR, params)


def duplicate_entry(message: str = ErrorMessage.DUPLICATE_ENTRY, params: Optional[Dict] = None) -> Response:
    """409 Conflict"""
    return handle_error(status.HTTP_409_CONFLICT, message, ErrorCode.DUPLICATE_ENTRY, params)


def server_error(message: str = ErrorMessage.INTERNAL_SERVER_ERROR, params: Optional[Dict] = None) -> Response:
    """500 Internal Server Error"""
    return handle_error(status.HTTP_500_INTERNAL_SERVER_ERROR, message, ErrorCode.INTERNAL_SERVER_ERROR, params)


def custom_exception_handler(exc: Exception, context: Dict[str, Any]) -> Response:
    """
    Custom exception handler that returns consistent error responses.
    Handles all Django and DRF exceptions comprehensively.
    """

    # Handle database-related exceptions before calling DRF's exception handler
    # as DRF doesn't handle these by default
    database_exceptions = (
        IntegrityError, OperationalError, ProgrammingError,
        DataError, DatabaseError, InternalError, NotSupportedError,
        ProtectedError, RestrictedError
    )

    django_core_exceptions = (
        ValidationError, ObjectDoesNotExist, MultipleObjectsReturned,
        PermissionDenied, SuspiciousOperation, FieldError, FieldDoesNotExist
    )

    if isinstance(exc, database_exceptions + django_core_exceptions):
        error = ErrorResponse.from_exception(exc)
        return error.to_response()

    # Let DRF handle its own exceptions first
    response = exception_handler(exc, context)

    if response is None:
        # For unhandled exceptions, create our own response
        error = ErrorResponse.from_exception(exc)
        response = error.to_response()
    else:
        # For handled exceptions, reformat the response to match our standard
        status_code = response.status_code

        # Extract error details
        if hasattr(exc, 'detail'):
            if isinstance(exc.detail, dict):
                error_params = {'field_errors': exc.detail}
                error_message = "Validation failed"
            elif isinstance(exc.detail, list):
                error_params = {'errors': exc.detail}
                error_message = "Multiple errors occurred"
            else:
                error_params = {}
                error_message = str(exc.detail)
        else:
            error_params = {}
            error_message = str(exc)

        # Map status code to error code
        error_code_map = {
            status.HTTP_400_BAD_REQUEST: ErrorCode.BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED: ErrorCode.UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN: ErrorCode.FORBIDDEN,
            status.HTTP_404_NOT_FOUND: ErrorCode.NOT_FOUND,
            status.HTTP_405_METHOD_NOT_ALLOWED: ErrorCode.METHOD_NOT_ALLOWED,
            status.HTTP_409_CONFLICT: ErrorCode.DUPLICATE_ENTRY,
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: ErrorCode.UNSUPPORTED_MEDIA_TYPE,
            status.HTTP_422_UNPROCESSABLE_ENTITY: ErrorCode.VALIDATION_ERROR,
            status.HTTP_429_TOO_MANY_REQUESTS: ErrorCode.TOO_MANY_REQUESTS,
        }

        error_code = error_code_map.get(
            status_code, ErrorCode.INTERNAL_SERVER_ERROR)

        # Create standardized response
        error = ErrorResponse(
            status_code=status_code,
            message=error_message,
            code=error_code,
            params=error_params
        )

        response.data = error.to_dict()

    return response


# Transaction error handler decorator
def handle_transaction_errors(func):
    """
    Decorator to handle database transaction errors in views
    Usage: @handle_transaction_errors
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if transaction.get_autocommit():
                # Not in a transaction, handle normally
                raise e
            else:
                # In a transaction, rollback and re-raise
                transaction.rollback()
                raise e
    return wrapper
