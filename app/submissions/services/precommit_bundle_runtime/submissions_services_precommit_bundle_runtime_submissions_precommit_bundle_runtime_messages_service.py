"""Application module for submissions services precommit bundle runtime submissions precommit bundle runtime messages service workflows."""

from __future__ import annotations

from app.submissions.services.precommit_bundle_runtime.submissions_services_precommit_bundle_runtime_submissions_precommit_bundle_runtime_core_model import (
    PRECOMMIT_MARKER_PREFIX,
)


def build_precommit_commit_marker(bundle_id: int, checksum: str) -> str:
    """Build precommit commit marker."""
    normalized_checksum = (checksum or "").strip().lower()
    return f"[{PRECOMMIT_MARKER_PREFIX} bundle_id={bundle_id} checksum={normalized_checksum}]"


def build_precommit_commit_message(bundle_id: int, checksum: str) -> str:
    """Build precommit commit message."""
    marker = build_precommit_commit_marker(bundle_id, checksum)
    return f"chore(winoe): apply scenario scaffolding\n\n{marker}"


__all__ = ["build_precommit_commit_marker", "build_precommit_commit_message"]
