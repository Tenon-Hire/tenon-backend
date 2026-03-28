"""Application module for submissions presentation submissions truncate utils workflows."""

from __future__ import annotations


def truncate_output(
    text: str | None, *, max_chars: int
) -> tuple[str | None, bool | None]:
    """Truncate output."""
    if text is None:
        return None, None
    if len(text) <= max_chars:
        return text, False
    return text[:max_chars] + "... (truncated)", True
