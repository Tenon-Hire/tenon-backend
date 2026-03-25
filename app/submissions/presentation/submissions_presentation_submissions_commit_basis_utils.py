from __future__ import annotations

from datetime import UTC, datetime


def resolve_commit_basis(sub, day_audit):
    cutoff_at = getattr(day_audit, "cutoff_at", None)
    if isinstance(cutoff_at, datetime) and cutoff_at.tzinfo is None:
        cutoff_at = cutoff_at.replace(tzinfo=UTC)
    cutoff_commit_sha = getattr(day_audit, "cutoff_commit_sha", None)
    return (
        cutoff_commit_sha or getattr(sub, "commit_sha", None),
        cutoff_commit_sha,
        cutoff_at,
        getattr(day_audit, "eval_basis_ref", None),
    )
