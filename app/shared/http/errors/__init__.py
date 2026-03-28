"""Error handler wiring for FastAPI."""

from app.shared.http.errors.shared_http_errors_handlers_utils import (
    api_error_handler,
    register_error_handlers,
)

__all__ = ["register_error_handlers", "api_error_handler"]
