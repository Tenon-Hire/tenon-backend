"""Application module for trials services trials template keys service workflows."""

from __future__ import annotations

from app.trials.constants.trials_constants_trials_template_keys_constants import (
    DEFAULT_TEMPLATE_KEY,
    validate_template_key,
)


def resolve_template_key(payload) -> str:
    """Resolve template key for current trial flows."""
    template_key = getattr(payload, "templateKey", DEFAULT_TEMPLATE_KEY)
    return validate_template_key(template_key)
