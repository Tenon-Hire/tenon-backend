"""Application module for utils normalization utils workflows."""

from __future__ import annotations


def normalize_email(value: str | None) -> str:
    """Normalize email."""
    if not isinstance(value, str):
        return ""
    return value.strip().lower()


__all__ = ["normalize_email"]
