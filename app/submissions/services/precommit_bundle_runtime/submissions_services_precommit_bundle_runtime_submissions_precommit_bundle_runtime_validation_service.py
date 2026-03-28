"""Application module for submissions services precommit bundle runtime submissions precommit bundle runtime validation service workflows."""

from __future__ import annotations

from app.shared.utils.shared_utils_errors_utils import ApiError


def validate_base_template_sha(base_template_sha: str | None, context) -> None:
    """Validate base template sha."""
    if not base_template_sha or not context.bundle.base_template_sha:
        return
    if base_template_sha == context.bundle.base_template_sha:
        return
    raise ApiError(
        status_code=500,
        detail="Precommit bundle base template SHA mismatch.",
        error_code="PRECOMMIT_BASE_SHA_MISMATCH",
        details={
            "baseTemplateSha": base_template_sha,
            "bundleBaseTemplateSha": context.bundle.base_template_sha,
            "scenarioVersionId": context.scenario_version_id,
            "templateKey": context.template_key,
        },
    )


__all__ = ["validate_base_template_sha"]
