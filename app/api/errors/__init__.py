"""Error handler wiring for FastAPI."""

from app.api.errors.handlers import register_error_handlers, api_error_handler

__all__ = ["register_error_handlers", "api_error_handler"]
