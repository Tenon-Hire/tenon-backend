"""Application module for submissions presentation submissions test results counts utils workflows."""

from __future__ import annotations

from app.submissions.presentation.submissions_presentation_submissions_parsed_output_utils_utils import (
    _safe_int,
)


def fill_counts(sub, passed_val, failed_val, total_val):
    """Execute fill counts."""
    if passed_val is None:
        passed_val = _safe_int(getattr(sub, "tests_passed", None))
    if failed_val is None:
        failed_val = _safe_int(getattr(sub, "tests_failed", None))
    if total_val is None:
        total_val = _safe_int(getattr(sub, "tests_total", None))
    if total_val is None and (passed_val is not None or failed_val is not None):
        total_val = (passed_val or 0) + (failed_val or 0)
    return passed_val, failed_val, total_val
