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
    commit_message: str | None = None,
    model_name: str | None = None,
    model_version: str | None = None,
    prompt_version: str | None = None,
    test_summary_json: dict | None = None,
    provenance_json: dict | None = None,
    last_error: str | None = None,
    commit: bool = True,
) -> PrecommitBundle:
    """Create bundle."""
    normalized_patch = patch_text if patch_text is not None else None
    normalized_storage_ref = (storage_ref or "").strip() or None
    normalized_status = normalize_status(status)
    validate_payload(
        normalized_patch,
        normalized_storage_ref,
        status=normalized_status,
    )
    resolved_checksum = None
    if normalized_patch is not None or normalized_storage_ref is not None:
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
        status=normalized_status,
        patch_text=normalized_patch,
        storage_ref=normalized_storage_ref,
        content_sha256=resolved_checksum,
        base_template_sha=base_template_sha,
        applied_commit_sha=applied_commit_sha,
        commit_message=(commit_message or "").strip() or None,
        model_name=(model_name or "").strip() or None,
        model_version=(model_version or "").strip() or None,
        prompt_version=(prompt_version or "").strip() or None,
        test_summary_json=test_summary_json,
        provenance_json=provenance_json,
        last_error=(last_error or "").strip() or None,
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


async def update_bundle(
    db: AsyncSession,
    *,
    bundle: PrecommitBundle,
    status: str | None = None,
    patch_text: str | None = None,
    storage_ref: str | None = None,
    base_template_sha: str | None = None,
    applied_commit_sha: str | None = None,
    commit_message: str | None = None,
    model_name: str | None = None,
    model_version: str | None = None,
    prompt_version: str | None = None,
    test_summary_json: dict | None = None,
    provenance_json: dict | None = None,
    last_error: str | None = None,
    commit: bool = True,
) -> PrecommitBundle:
    """Update bundle state and optional artifact/provenance fields."""
    resolved_status = normalize_status(status or bundle.status)
    resolved_patch = patch_text if patch_text is not None else bundle.patch_text
    resolved_storage_ref = (
        (storage_ref or "").strip() or None
        if storage_ref is not None
        else bundle.storage_ref
    )
    validate_payload(
        resolved_patch,
        resolved_storage_ref,
        status=resolved_status,
    )
    bundle.status = resolved_status
    bundle.patch_text = resolved_patch
    bundle.storage_ref = resolved_storage_ref
    bundle.content_sha256 = (
        compute_content_sha256(
            patch_text=resolved_patch,
            storage_ref=resolved_storage_ref,
        )
        if resolved_patch is not None or resolved_storage_ref is not None
        else None
    )
    if base_template_sha is not None:
        bundle.base_template_sha = (base_template_sha or "").strip() or None
    if applied_commit_sha is not None:
        bundle.applied_commit_sha = (applied_commit_sha or "").strip() or None
    if commit_message is not None:
        bundle.commit_message = (commit_message or "").strip() or None
    if model_name is not None:
        bundle.model_name = (model_name or "").strip() or None
    if model_version is not None:
        bundle.model_version = (model_version or "").strip() or None
    if prompt_version is not None:
        bundle.prompt_version = (prompt_version or "").strip() or None
    bundle.test_summary_json = test_summary_json
    bundle.provenance_json = provenance_json
    if last_error is not None:
        bundle.last_error = (last_error or "").strip() or None
    if commit:
        await db.commit()
        await db.refresh(bundle)
    else:
        await db.flush()
    return bundle
