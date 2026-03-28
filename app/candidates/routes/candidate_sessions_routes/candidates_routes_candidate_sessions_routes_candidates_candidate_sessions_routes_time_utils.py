"""Application module for candidates routes candidate sessions routes candidates candidate sessions routes time utils workflows."""

from __future__ import annotations

from datetime import UTC, datetime


def utcnow():
    """Execute utcnow."""
    return datetime.now(UTC)


__all__ = ["utcnow"]
