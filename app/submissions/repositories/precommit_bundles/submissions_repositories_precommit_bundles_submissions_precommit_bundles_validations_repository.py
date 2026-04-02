"""Application module for submissions repositories precommit bundles submissions precommit bundles validations repository workflows."""

from __future__ import annotations

import hashlib

from app.submissions.repositories.precommit_bundles.submissions_repositories_precommit_bundles_submissions_precommit_bundles_core_model import (
    PRECOMMIT_BUNDLE_STATUS_READY,
    PRECOMMIT_BUNDLE_STATUSES,
)

MAX_PATCH_TEXT_BYTES = 250_000


def normalize_template_key(value: str) -> str:
    """Normalize template key."""
    normalized = (value or "").strip()
    if not normalized:
        raise ValueError("template_key must be non-empty")
    return normalized


def normalize_status(status: str) -> str:
    """Normalize status."""
    normalized = (status or "").strip().lower()
    if normalized not in PRECOMMIT_BUNDLE_STATUSES:
        raise ValueError(f"invalid precommit bundle status: {status}")
    return normalized


def validate_payload(
    patch_text: str | None,
    storage_ref: str | None,
    *,
    status: str | None = None,
) -> None:
    """Validate payload."""
    normalized_patch = patch_text if patch_text is not None else None
    normalized_ref = (storage_ref or "").strip() or None
    normalized_status = normalize_status(status) if status is not None else None
    if (
        normalized_patch is None
        and normalized_ref is None
        and normalized_status != PRECOMMIT_BUNDLE_STATUS_READY
    ):
        return
    if normalized_patch is None and normalized_ref is None:
        raise ValueError("patch_text or storage_ref is required")
    if normalized_patch is not None:
        patch_size = len(normalized_patch.encode("utf-8"))
        if patch_size > MAX_PATCH_TEXT_BYTES:
            raise ValueError("patch_text exceeds max size")


def compute_content_sha256(
    *, patch_text: str | None = None, storage_ref: str | None = None
) -> str:
    """Compute content sha256."""
    validate_payload(patch_text, storage_ref, status=PRECOMMIT_BUNDLE_STATUS_READY)
    source = patch_text if patch_text is not None else f"storage_ref:{storage_ref}"
    return hashlib.sha256(source.encode("utf-8")).hexdigest()
