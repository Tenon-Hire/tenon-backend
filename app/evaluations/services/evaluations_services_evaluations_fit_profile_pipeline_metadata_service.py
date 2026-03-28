"""Application module for evaluations services evaluations fit profile pipeline metadata service workflows."""

from __future__ import annotations

from typing import Any

from app.evaluations.services.evaluations_services_evaluations_fit_profile_pipeline_basis_service import (
    _build_basis_references,
    _stable_hash,
    _transcript_basis_hash,
)
from app.shared.database.shared_database_models_model import (
    CandidateDayAudit,
    Submission,
    Transcript,
)


def _resolve_cutoff_commit_shas(
    *,
    day_audits: dict[int, CandidateDayAudit],
    submissions_by_day: dict[int, Submission],
) -> tuple[str, str, str]:
    day2_submission = submissions_by_day.get(2)
    day3_submission = submissions_by_day.get(3)
    day2_checkpoint_sha = (
        (day_audits.get(2).cutoff_commit_sha if day_audits.get(2) is not None else None)
        or (day2_submission.checkpoint_sha if day2_submission is not None else None)
        or (day2_submission.commit_sha if day2_submission is not None else None)
        or "day2-missing"
    )
    day3_final_sha = (
        (day_audits.get(3).cutoff_commit_sha if day_audits.get(3) is not None else None)
        or (day3_submission.final_sha if day3_submission is not None else None)
        or (day3_submission.commit_sha if day3_submission is not None else None)
        or "day3-missing"
    )
    cutoff_commit_sha = (
        day3_final_sha if day3_final_sha != "day3-missing" else day2_checkpoint_sha
    )
    return day2_checkpoint_sha, day3_final_sha, cutoff_commit_sha


def _build_run_metadata(
    *,
    context,
    scenario_rubric_version: str,
    day_audits: dict[int, CandidateDayAudit],
    submissions_by_day: dict[int, Submission],
    transcript_reference: str,
    transcript: Transcript | None,
    disabled_days: list[int],
    enabled_days: list[int],
    requested_by_user_id: int | None,
    job_id: str | None,
) -> tuple[dict[str, Any], dict[str, Any], str, str, str]:
    basis_refs = _build_basis_references(
        scenario_version_id=context.candidate_session.scenario_version_id,
        scenario_rubric_version=scenario_rubric_version,
        day_audits=day_audits,
        submissions_by_day=submissions_by_day,
        transcript_reference=transcript_reference,
        transcript_hash=_transcript_basis_hash(transcript),
        disabled_day_indexes=disabled_days,
    )
    basis_fingerprint = _stable_hash(
        {
            "candidateSessionId": context.candidate_session.id,
            "simulationId": context.simulation.id,
            "scenarioVersionId": context.candidate_session.scenario_version_id,
            "basis": basis_refs,
        }
    )
    (
        day2_checkpoint_sha,
        day3_final_sha,
        cutoff_commit_sha,
    ) = _resolve_cutoff_commit_shas(
        day_audits=day_audits,
        submissions_by_day=submissions_by_day,
    )
    run_metadata = {
        "jobId": job_id,
        "basisFingerprint": basis_fingerprint,
        "disabledDayIndexes": disabled_days,
        "enabledDayIndexes": enabled_days,
        "basisRefs": basis_refs,
        "requestedByUserId": requested_by_user_id,
    }
    return (
        run_metadata,
        basis_refs,
        day2_checkpoint_sha,
        day3_final_sha,
        cutoff_commit_sha,
    )


__all__ = ["_build_run_metadata"]
