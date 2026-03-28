"""Application module for http errors handlers utils workflows."""

from __future__ import annotations

from fastapi.exceptions import RequestValidationError

from app.shared.http.errors.shared_http_errors_response_utils import api_error_handler
from app.shared.http.errors.shared_http_errors_validation_utils import (
    validation_error_handler,
)
from app.shared.utils.shared_utils_errors_utils import ApiError


def register_error_handlers(app) -> None:
    """Execute register error handlers."""
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)


__all__ = ["api_error_handler", "register_error_handlers"]
