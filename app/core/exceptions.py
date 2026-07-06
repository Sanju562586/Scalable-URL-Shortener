"""
Custom application exceptions with pre-configured HTTP status codes.
All exceptions are subclasses of FastAPI's HTTPException so they are
handled automatically by FastAPI's default exception handlers.
"""

from fastapi import HTTPException, status


class ShortCodeNotFound(HTTPException):
    """Raised when a short code does not exist in the database."""

    def __init__(self, short_code: str) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Short code '{short_code}' not found.",
        )


class ShortCodeExpired(HTTPException):
    """Raised when a short URL has passed its expiry timestamp."""

    def __init__(self, short_code: str) -> None:
        super().__init__(
            status_code=status.HTTP_410_GONE,
            detail=f"Short URL '{short_code}' has expired.",
        )


class ShortCodeInactive(HTTPException):
    """Raised when a short URL has been deactivated by its owner."""

    def __init__(self, short_code: str) -> None:
        super().__init__(
            status_code=status.HTTP_410_GONE,
            detail=f"Short URL '{short_code}' is no longer active.",
        )


class CustomCodeConflict(HTTPException):
    """Raised when a requested custom alias is already taken."""

    def __init__(self, code: str) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Custom code '{code}' is already in use. Choose another.",
        )


class InvalidAPIKey(HTTPException):
    """Raised when the provided API key is missing or invalid."""

    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )


class URLNotOwnedByKey(HTTPException):
    """Raised when an API key tries to modify a URL it does not own."""

    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this URL.",
        )
