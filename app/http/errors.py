from __future__ import annotations
from typing import Any


class AppError(Exception):
    """base domain / app exception wtih API friendly metadata"""

    status_code = 400
    error_code = "APP_ERROR"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationError(AppError):
    status_code = 422
    error_code = "VALIDATION_ERROR"


class AuthenticationError(AppError):
    status_code = 401
    error_code = "AUTHENTICATION ERROR"


class AuthorizationError(AppError):
    status_code = 403
    error_code = "AUTHORIZATION_ERROR"


class NotFoundError(AppError):
    status_code = 404
    error_code = "RESOURCE_NOT_FOUND"


class ConflictError(AppError):
    status_code = 409
    error_code = "CONFLICT"


class ExternalAPIError(AppError):
    status_code = 502
    error_code = "EXTERNAL_API_ERROR"


class ServiceUnavailableError(AppError):
    status_code = 503
    error_code = "SERVICE_UNAVAILABLE"