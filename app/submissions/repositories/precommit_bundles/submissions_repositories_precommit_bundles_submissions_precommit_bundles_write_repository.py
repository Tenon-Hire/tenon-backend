"""Application module for submissions repositories precommit bundles submissions precommit bundles write repository workflows."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.submissions.repositories.precommit_bundles.submissions_repositories_precommit_bundles_submissions_precommit_bundles_core_model import (
    PrecommitBundle,
)

from .submissions_repositories_precommit_bundles_submissions_precommit_bundles_validations_repository import (
    compute_content_sha256,
    normalize_status,
    normalize_template_key,
    validate_payload,
)


async def create_bundle(
    db: AsyncSession,
    *,
    scenario_version_id: int,
    template_key: str,
    status: str,
    patch_text: str | None = None,
    storage_ref: str | None = None,
    base_template_sha: str | None = None,
    applied_commit_sha: str | None = None,
    content_sha256: str | None = None,
    commit: bool = True,
) -> PrecommitBundle:
    """Create bundle."""
    normalized_patch = patch_text if patch_text is not None else None
    normalized_storage_ref = (storage_ref or "").strip() or None
    validate_payload(normalized_patch, normalized_storage_ref)
    resolved_checksum = (
        content_sha256.strip().lower()
        if isinstance(content_sha256, str) and content_sha256.strip()
        else compute_content_sha256(
            patch_text=normalized_patch,
            storage_ref=normalized_storage_ref,
        )
    )
    bundle = PrecommitBundle(
        scenario_version_id=scenario_version_id,
        template_key=normalize_template_key(template_key),
        status=normalize_status(status),
        patch_text=normalized_patch,
        storage_ref=normalized_storage_ref,
        content_sha256=resolved_checksum,
        base_template_sha=base_template_sha,
        applied_commit_sha=applied_commit_sha,
    )
    db.add(bundle)
    if commit:
        await db.commit()
        await db.refresh(bundle)
    else:
        await db.flush()
    return bundle


async def set_status(
    db: AsyncSession,
    *,
    bundle: PrecommitBundle,
    status: str,
    commit: bool = True,
) -> PrecommitBundle:
    """Set status."""
    bundle.status = normalize_status(status)
    if commit:
        await db.commit()
        await db.refresh(bundle)
    else:
        await db.flush()
    return bundle


async def set_applied_commit_sha(
    db: AsyncSession,
    *,
    bundle: PrecommitBundle,
    applied_commit_sha: str | None,
    commit: bool = True,
) -> PrecommitBundle:
    """Set applied commit sha."""
    bundle.applied_commit_sha = (applied_commit_sha or "").strip() or None
    if commit:
        await db.commit()
        await db.refresh(bundle)
    else:
        await db.flush()
    return bundle
