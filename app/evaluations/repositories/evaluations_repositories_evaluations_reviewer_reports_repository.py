"""Application module for evaluations repositories reviewer reports workflows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.candidate_sessions.repositories.candidates_candidate_sessions_repositories_candidates_candidate_sessions_candidate_session_model import (
    CandidateSession,
)
from app.evaluations.repositories.evaluations_repositories_evaluations_core_model import (
    EvaluationReviewerReport,
    EvaluationRun,
)
from app.evaluations.repositories.evaluations_repositories_evaluations_validation_evidence_repository import (
    validate_evidence_pointers,
)
from app.evaluations.repositories.evaluations_repositories_evaluations_validation_scalars_repository import (
    coerce_day_index,
    coerce_object,
    coerce_score,
    normalize_non_empty_str,
)
from app.trials.repositories.trials_repositories_trials_trial_model import Trial


def _normalize_text_list(value: Any, *, field_path: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{field_path} must be a list.")
    normalized: list[str] = []
    for idx, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{field_path}[{idx}] must be a non-empty string.")
        normalized.append(item.strip())
    return normalized


def _normalize_evidence_citations(
    value: Any,
) -> list[dict[str, Any]]:
    """Normalize reviewer evidence through the canonical Evidence Trail pointer contract."""
    return validate_evidence_pointers(value)


def normalize_reviewer_report_payload(
    reviewer_reports: Sequence[Mapping[str, Any]], *, allow_empty: bool
) -> list[dict[str, Any]]:
    if isinstance(reviewer_reports, str | bytes):
        raise ValueError("reviewer_reports must be a sequence of objects.")
    if not reviewer_reports:
        if allow_empty:
            return []
        raise ValueError("reviewer_reports must include at least one report.")
    normalized: list[dict[str, Any]] = []
    seen_keys: set[tuple[int, str, int]] = set()
    for idx, entry in enumerate(reviewer_reports):
        field_path = f"reviewer_reports[{idx}]"
        if not isinstance(entry, Mapping):
            raise ValueError(f"{field_path} must be an object.")
        day_index = coerce_day_index(
            entry.get("day_index"), field_path=f"{field_path}.day_index"
        )
        reviewer_agent_key = normalize_non_empty_str(
            entry.get("reviewer_agent_key"),
            field_name=f"{field_path}.reviewer_agent_key",
        )
        submission_kind = normalize_non_empty_str(
            entry.get("submission_kind"), field_name=f"{field_path}.submission_kind"
        ).lower()
        identity = (day_index, reviewer_agent_key, submission_kind)
        if identity in seen_keys:
            raise ValueError(
                "reviewer_reports contains duplicate reviewer/day/submission entries."
            )
        seen_keys.add(identity)
        normalized.append(
            {
                "day_index": day_index,
                "reviewer_agent_key": reviewer_agent_key,
                "submission_kind": submission_kind,
                "score": coerce_score(
                    entry.get("score"), field_path=f"{field_path}.score"
                ),
                "dimensional_scores_json": coerce_object(
                    entry.get("dimensional_scores_json"),
                    field_name=f"{field_path}.dimensional_scores_json",
                )
                or {},
                "evidence_citations_json": _normalize_evidence_citations(
                    entry.get("evidence_citations_json")
                ),
                "assessment_text": normalize_non_empty_str(
                    entry.get("assessment_text"),
                    field_name=f"{field_path}.assessment_text",
                ),
                "strengths_json": _normalize_text_list(
                    entry.get("strengths_json") or [],
                    field_path=f"{field_path}.strengths_json",
                ),
                "risks_json": _normalize_text_list(
                    entry.get("risks_json") or [],
                    field_path=f"{field_path}.risks_json",
                ),
                "raw_output_json": coerce_object(
                    entry.get("raw_output_json"),
                    field_name=f"{field_path}.raw_output_json",
                ),
            }
        )
    return normalized


async def add_reviewer_reports(
    db: AsyncSession,
    *,
    run: EvaluationRun,
    reviewer_reports: Sequence[Mapping[str, Any]],
    allow_empty: bool = False,
    commit: bool = True,
) -> list[EvaluationReviewerReport]:
    if run.id is None:
        raise ValueError("run must be persisted before adding reviewer reports.")
    normalized_entries = normalize_reviewer_report_payload(
        reviewer_reports, allow_empty=allow_empty
    )
    if not normalized_entries:
        await (db.commit() if commit else db.flush())
        return []

    existing_rows = (
        (
            await db.execute(
                select(EvaluationReviewerReport).where(
                    EvaluationReviewerReport.run_id == run.id
                )
            )
        )
        .scalars()
        .all()
    )
    existing_by_identity = {
        (row.day_index, row.reviewer_agent_key, row.submission_kind): row
        for row in existing_rows
    }
    created: list[EvaluationReviewerReport] = []
    for entry in normalized_entries:
        identity = (
            int(entry["day_index"]),
            str(entry["reviewer_agent_key"]),
            str(entry["submission_kind"]),
        )
        existing = existing_by_identity.get(identity)
        if existing is not None:
            comparable_existing = {
                "score": float(existing.score),
                "dimensional_scores_json": dict(existing.dimensional_scores_json or {}),
                "evidence_citations_json": list(existing.evidence_citations_json or []),
                "assessment_text": existing.assessment_text,
                "strengths_json": list(existing.strengths_json or []),
                "risks_json": list(existing.risks_json or []),
                "raw_output_json": (
                    dict(existing.raw_output_json)
                    if isinstance(existing.raw_output_json, Mapping)
                    else None
                ),
            }
            comparable_new = {
                "score": float(entry["score"]),
                "dimensional_scores_json": dict(entry["dimensional_scores_json"]),
                "evidence_citations_json": list(entry["evidence_citations_json"]),
                "assessment_text": str(entry["assessment_text"]),
                "strengths_json": list(entry["strengths_json"]),
                "risks_json": list(entry["risks_json"]),
                "raw_output_json": (
                    dict(entry["raw_output_json"])
                    if isinstance(entry["raw_output_json"], Mapping)
                    else None
                ),
            }
            if comparable_existing != comparable_new:
                raise ValueError(
                    "run already has reviewer report for day_index, reviewer_agent_key, "
                    "and submission_kind with different persisted content."
                )
            created.append(existing)
            continue
        report = EvaluationReviewerReport(
            run=run,
            day_index=int(entry["day_index"]),
            reviewer_agent_key=str(entry["reviewer_agent_key"]),
            submission_kind=str(entry["submission_kind"]),
            score=float(entry["score"]),
            dimensional_scores_json=dict(entry["dimensional_scores_json"]),
            evidence_citations_json=list(entry["evidence_citations_json"]),
            assessment_text=str(entry["assessment_text"]),
            strengths_json=list(entry["strengths_json"]),
            risks_json=list(entry["risks_json"]),
            raw_output_json=entry["raw_output_json"],
        )
        created.append(report)
        db.add(report)
    if commit:
        await db.commit()
        for row in created:
            await db.refresh(row)
    else:
        await db.flush()
    return created


async def list_reviewer_reports(
    db: AsyncSession,
    *,
    run_id: int | None = None,
    candidate_session_id: int | None = None,
    trial_id: int | None = None,
    reviewer_agent_key: str | None = None,
    day_index: int | None = None,
    submission_kind: str | None = None,
) -> list[EvaluationReviewerReport]:
    stmt = select(EvaluationReviewerReport).join(
        EvaluationRun, EvaluationRun.id == EvaluationReviewerReport.run_id
    )
    if run_id is not None:
        stmt = stmt.where(EvaluationReviewerReport.run_id == int(run_id))
    if candidate_session_id is not None:
        stmt = stmt.where(
            EvaluationRun.candidate_session_id == int(candidate_session_id)
        )
    if trial_id is not None:
        stmt = (
            stmt.join(
                CandidateSession,
                CandidateSession.id == EvaluationRun.candidate_session_id,
            )
            .join(Trial, Trial.id == CandidateSession.trial_id)
            .where(Trial.id == int(trial_id))
        )
    if reviewer_agent_key is not None:
        stmt = stmt.where(
            EvaluationReviewerReport.reviewer_agent_key == reviewer_agent_key
        )
    if day_index is not None:
        stmt = stmt.where(EvaluationReviewerReport.day_index == int(day_index))
    if submission_kind is not None:
        stmt = stmt.where(
            EvaluationReviewerReport.submission_kind == submission_kind.strip().lower()
        )
    stmt = stmt.order_by(
        EvaluationReviewerReport.day_index.asc(),
        EvaluationReviewerReport.reviewer_agent_key.asc(),
        EvaluationReviewerReport.id.asc(),
    )
    rows = (await db.execute(stmt)).scalars().all()
    return rows


async def list_reviewer_reports_for_run(
    db: AsyncSession, *, run_id: int
) -> list[EvaluationReviewerReport]:
    return await list_reviewer_reports(db, run_id=run_id)
