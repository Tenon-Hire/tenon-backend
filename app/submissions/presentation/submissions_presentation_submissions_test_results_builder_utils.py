"""Application module for submissions presentation submissions test results builder utils workflows."""

from __future__ import annotations

from app.submissions.presentation.submissions_presentation_submissions_test_results_assemble_utils import (
    assemble_result,
)
from app.submissions.presentation.submissions_presentation_submissions_test_results_counts_utils import (
    fill_counts,
)
from app.submissions.presentation.submissions_presentation_submissions_test_results_guard_utils import (
    should_skip,
)
from app.submissions.presentation.submissions_presentation_submissions_test_results_kwargs_utils import (
    build_result_kwargs,
)
from app.submissions.presentation.submissions_presentation_submissions_test_results_payload_utils import (
    extract_payload,
)
from app.submissions.presentation.submissions_presentation_submissions_test_results_runinfo_utils import (
    enrich_run_info,
)
from app.submissions.services import (
    service_talent_partner as talent_partner_sub_service,
)


def build_test_results(
    sub,
    parsed_output,
    *,
    workflow_url: str | None,
    commit_url: str | None,
    include_output: bool,
    max_output_chars: int,
    commit_sha_override: str | None = None,
):
    """Build test results."""
    parsed_payload = parsed_output or None
    payload = extract_payload(
        parsed_payload, include_output=include_output, max_output_chars=max_output_chars
    )
    passed_val, failed_val, total_val = fill_counts(
        sub, payload["passed_val"], payload["failed_val"], payload["total_val"]
    )
    status_str = talent_partner_sub_service.derive_test_status(
        passed_val, failed_val, parsed_payload
    )
    (
        run_id,
        conclusion,
        timeout,
        run_status,
        workflow_run_id_str,
        commit_sha,
        last_run_at,
    ) = enrich_run_info(
        sub, payload["run_id"], payload["conclusion"], payload["timeout"]
    )
    if commit_sha_override is not None:
        commit_sha = commit_sha_override
    if should_skip(
        status_str,
        passed_val,
        failed_val,
        total_val,
        payload["sanitized_output"],
        workflow_run_id_str,
        commit_sha,
        last_run_at,
    ):
        return None
    kwargs = build_result_kwargs(
        status_str=status_str,
        passed_val=passed_val,
        failed_val=failed_val,
        total_val=total_val,
        run_id=run_id,
        run_status=run_status,
        conclusion=conclusion,
        timeout=timeout,
        payload=payload,
        last_run_at=last_run_at,
        workflow_run_id_str=workflow_run_id_str,
        commit_sha=commit_sha,
        workflow_url=workflow_url,
        commit_url=commit_url,
        include_output=include_output,
    )
    return assemble_result(**kwargs)
