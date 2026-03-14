from __future__ import annotations


class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found.") -> None:
        super().__init__("not_found", message, status_code=404)


class PermissionDeniedError(AppError):
    def __init__(self, message: str = "Permission denied.") -> None:
        super().__init__("permission_denied", message, status_code=403)


class ConflictError(AppError):
    def __init__(self, message: str = "Conflict detected.") -> None:
        super().__init__("conflict", message, status_code=409)


class ValidationError(AppError):
    def __init__(self, message: str = "Validation failed.") -> None:
        super().__init__("validation_error", message, status_code=422)


class AuthenticationError(AppError):
    def __init__(self, message: str = "Authentication required.") -> None:
        super().__init__("authentication_error", message, status_code=401)


class ExternalServiceError(AppError):
    def __init__(self, message: str = "External service failed.") -> None:
        super().__init__("external_service_error", message, status_code=502)

