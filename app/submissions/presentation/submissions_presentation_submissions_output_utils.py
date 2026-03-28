"""Application module for submissions presentation submissions output utils workflows."""

from __future__ import annotations

import json

from app.submissions.presentation.submissions_presentation_submissions_core_constants import (
    MAX_OUTPUT_CHARS_DETAIL,
    MAX_OUTPUT_CHARS_LIST,
)


def parse_diff_summary(raw: str | None):
    """Parse diff summary."""
    if not raw:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return None


def max_output_chars(include_output: bool) -> int:
    """Execute max output chars."""
    return MAX_OUTPUT_CHARS_DETAIL if include_output else MAX_OUTPUT_CHARS_LIST
