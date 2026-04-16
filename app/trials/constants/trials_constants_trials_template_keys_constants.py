"""Application module for trial template-key constants."""

from __future__ import annotations

from app.trials.constants.trials_constants_trials_defaults_constants import (
    DEFAULT_TEMPLATE_KEY,
)

# Keep the allowed set as a contract for validation error details.
ALLOWED_TEMPLATE_KEYS: set[str] = {
    "python-fastapi",
    "node-express-ts",
    "node-nest-ts",
    "java-springboot",
    "go-gin",
    "dotnet-webapi",
    "monorepo-nextjs-nest",
    "monorepo-nextjs-fastapi",
    "monorepo-react-express",
    "monorepo-react-springboot",
    "mobile-fullstack-expo-fastapi",
    "mobile-backend-fastapi",
    "ml-backend-fastapi",
    "ml-infra-mlops",
}


class TemplateKeyError(ValueError):
    """Raised when a template key cannot be normalized."""


def validate_template_key(template_key: str | None) -> str:
    """Normalize a template key for current trial flows.

    The current product accepts custom template keys, so this only trims input
    and falls back to the default when the value is blank.
    """
    if template_key is None:
        return DEFAULT_TEMPLATE_KEY
    if not isinstance(template_key, str):
        raise TemplateKeyError("templateKey must be a string")
    normalized = template_key.strip()
    return normalized or DEFAULT_TEMPLATE_KEY


__all__ = [
    "ALLOWED_TEMPLATE_KEYS",
    "DEFAULT_TEMPLATE_KEY",
    "TemplateKeyError",
    "validate_template_key",
]
