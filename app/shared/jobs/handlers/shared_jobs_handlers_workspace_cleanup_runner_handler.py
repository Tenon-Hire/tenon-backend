"""Application module for jobs handlers workspace cleanup runner handler workflows."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.shared.jobs.handlers.shared_jobs_handlers_workspace_cleanup_processing_handler import (
    _process_cleanup_target,
)
from app.shared.jobs.handlers.shared_jobs_handlers_workspace_cleanup_utils import (
    _parse_positive_int,
    _resolve_cleanup_config,
)


async def handle_workspace_cleanup_impl(
    payload_json: dict[str, Any], **deps
) -> dict[str, Any]:
    """Handle workspace cleanup impl."""
    company_id = _parse_positive_int(payload_json.get("companyId"))
    if company_id is None:
        return {"status": "skipped_invalid_payload", "companyId": company_id}

    config = _resolve_cleanup_config()
    now = datetime.now(UTC)
    job_id_raw = payload_json.get("jobId")
    job_id = str(job_id_raw).strip() if isinstance(job_id_raw, str) else None
    github_client = deps["get_github_client"]()
    summary: dict[str, int] = {
        "candidateCount": 0,
        "processed": 0,
        "revoked": 0,
        "archived": 0,
        "deleted": 0,
        "failed": 0,
        "pending": 0,
        "alreadyCleaned": 0,
        "skippedActive": 0,
    }

    async with deps["async_session_maker"]() as db:
        targets = await deps["_list_company_cleanup_targets"](db, company_id=company_id)
        summary["candidateCount"] = len(targets)
        deps["logger"].info(
            "workspace_cleanup_started",
            extra={
                "jobId": job_id,
                "companyId": company_id,
                "countCandidates": summary["candidateCount"],
            },
        )
        candidate_session_ids = sorted(
            {target.candidate_session.id for target in targets}
        )
        cutoff_session_ids = await deps["_load_sessions_with_cutoff"](
            db,
            candidate_session_ids=candidate_session_ids,
        )
        for target in targets:
            await _process_cleanup_target(
                db=db,
                target=target,
                now=now,
                config=config,
                github_client=github_client,
                cutoff_session_ids=cutoff_session_ids,
                summary=summary,
                job_id=job_id,
                logger=deps["logger"],
                enforce_collaborator_revocation=deps[
                    "_enforce_collaborator_revocation"
                ],
                apply_retention_cleanup=deps["_apply_retention_cleanup"],
            )

    return {
        "status": "completed",
        "companyId": company_id,
        "cleanupMode": config.cleanup_mode,
        "retentionDays": config.retention_days,
        **summary,
    }


__all__ = ["handle_workspace_cleanup_impl"]
