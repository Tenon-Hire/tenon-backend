"""Application module for submissions presentation submissions parsed output utils workflows."""

from __future__ import annotations

from app.submissions.presentation.submissions_presentation_submissions_parsed_output_dict_utils import (
    process_dict_output,
)
from app.submissions.presentation.submissions_presentation_submissions_parsed_output_string_utils import (
    process_string_output,
)
from app.submissions.presentation.submissions_presentation_submissions_parsed_output_utils_utils import (
    _safe_int,
)


def process_parsed_output(
    parsed_output, *, include_output: bool, max_output_chars: int
):
    """Process parsed output."""
    if isinstance(parsed_output, dict):
        if not parsed_output:
            return (None,) * 13
        return process_dict_output(
            parsed_output,
            include_output=include_output,
            max_output_chars=max_output_chars,
        )
    if isinstance(parsed_output, str):
        return process_string_output(
            parsed_output,
            include_output=include_output,
            max_output_chars=max_output_chars,
        )
    return (None,) * 13


__all__ = ["process_parsed_output", "_safe_int"]
