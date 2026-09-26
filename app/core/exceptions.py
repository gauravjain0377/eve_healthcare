from typing import Any, Optional
from fastapi import HTTPException, status


class AppException(HTTPException):
    """Base application exception."""
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: str = "ERROR",
        headers: Optional[dict[str, str]] = None
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_code = error_code


class NotFoundException(AppException):
    def __init__(self, resource: str, identifier: Any):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} with identifier '{identifier}' was not found.",
            error_code=f"{resource.upper()}_NOT_FOUND"
        )


class ConflictException(AppException):
    def __init__(self, detail: str, error_code: str = "RESOURCE_CONFLICT"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            error_code=error_code
        )


class BadRequestException(AppException):
    def __init__(self, detail: str, error_code: str = "BAD_REQUEST"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code=error_code
        )


class UnauthorizedException(AppException):
    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code="UNAUTHORIZED",
            headers={"WWW-Authenticate": "Bearer"}
        )


class ForbiddenException(AppException):
    def __init__(self, detail: str = "Not enough privileges"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code="FORBIDDEN"
        )
