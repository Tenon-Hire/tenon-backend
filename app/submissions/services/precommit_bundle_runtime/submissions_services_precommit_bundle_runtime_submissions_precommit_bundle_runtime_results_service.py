"""Application module for submissions services precommit bundle runtime submissions precommit bundle runtime results service workflows."""

from __future__ import annotations

from app.submissions.services.precommit_bundle_runtime.submissions_services_precommit_bundle_runtime_submissions_precommit_bundle_runtime_core_model import (
    PrecommitBundleApplyResult,
)


def result_already_applied(
    precommit_sha: str,
    *,
    bundle_id: int | None,
    reason: str,
) -> PrecommitBundleApplyResult:
    """Execute result already applied."""
    details: dict[str, object] = {"reason": reason}
    if bundle_id is not None:
        details["bundleId"] = bundle_id
    return PrecommitBundleApplyResult(
        state="already_applied",
        precommit_sha=precommit_sha,
        bundle_id=bundle_id,
        details=details,
    )


def result_no_bundle(**details: object) -> PrecommitBundleApplyResult:
    """Execute result no bundle."""
    return PrecommitBundleApplyResult(
        state="no_bundle",
        precommit_sha=None,
        bundle_id=None,
        details=details,
    )


def result_applied(precommit_sha: str, *, bundle_id: int) -> PrecommitBundleApplyResult:
    """Execute result applied."""
    return PrecommitBundleApplyResult(
        state="applied",
        precommit_sha=precommit_sha,
        bundle_id=bundle_id,
        details={"reason": "commit_created", "bundleId": bundle_id},
    )


__all__ = ["result_already_applied", "result_applied", "result_no_bundle"]
