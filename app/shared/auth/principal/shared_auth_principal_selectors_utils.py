"""Application module for auth principal selectors utils workflows."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.shared.utils.shared_utils_normalization_utils import normalize_email


def first_claim(
    claims: dict[str, Any], keys: Iterable[str], *, default: Any | None = None
):
    """Execute first claim."""
    for key in keys:
        if key and key in claims:
            return claims[key]
    return default


__all__ = ["first_claim", "normalize_email"]
