"""Compatibility wrappers for error handling (kept slim for legacy imports)."""
from __future__ import annotations

from app.shared.http.errors.shared_http_errors_handlers_utils import (
    register_error_handlers,
)
from app.shared.http.errors.shared_http_errors_mappers_utils import map_github_error
from app.shared.http.errors.shared_http_errors_response_utils import api_error_handler
from app.shared.http.errors.shared_http_errors_validation_utils import (
    validation_error_handler,
)
from app.shared.utils.shared_utils_errors_utils import ApiError

__all__ = [
    "ApiError",
    "api_error_handler",
    "register_error_handlers",
    "map_github_error",
    "validation_error_handler",
]
