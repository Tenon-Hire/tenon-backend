"""Application module for submissions services task drafts submissions task drafts finalization service workflows."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

NO_DRAFT_AT_CUTOFF_MARKER: dict[str, Any] = {
    "_winoe": {
        "noContent": True,
        "reason": "NO_DRAFT_AT_CUTOFF",
    }
}


def build_submission_payload(
    *,
    content_text: str | None,
    content_json: dict[str, Any] | None,
):
    """Build submission payload."""
    return SimpleNamespace(contentText=content_text, contentJson=content_json)


__all__ = ["NO_DRAFT_AT_CUTOFF_MARKER", "build_submission_payload"]
