"""Compatibility template-key helpers for current trial flows."""

from __future__ import annotations

from app.trials.constants.trials_constants_trials_template_keys_constants import (
    ALLOWED_TEMPLATE_KEYS,
    DEFAULT_TEMPLATE_KEY,
    TemplateKeyError,
    validate_template_key,
)

__all__ = [
    "ALLOWED_TEMPLATE_KEYS",
    "DEFAULT_TEMPLATE_KEY",
    "TemplateKeyError",
    "validate_template_key",
]
