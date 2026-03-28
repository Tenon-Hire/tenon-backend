"""Application module for evaluations repositories evaluations day scores repository workflows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.evaluations.repositories.evaluations_repositories_evaluations_core_model import (
    EvaluationDayScore,
    EvaluationRun,
)
from app.evaluations.repositories.evaluations_repositories_evaluations_validation_evidence_repository import (
    validate_evidence_pointers,
)
from app.evaluations.repositories.evaluations_repositories_evaluations_validation_scalars_repository import (
    coerce_day_index,
    coerce_rubric_results_json,
    coerce_score,
)


def normalize_day_score_payload(
    day_scores: Sequence[Mapping[str, Any]], *, allow_empty: bool
) -> list[dict[str, Any]]:
    """Normalize day score payload."""
    if isinstance(day_scores, str | bytes):
        raise ValueError("day_scores must be a sequence of objects.")
    if not day_scores:
        if allow_empty:
            return []
        raise ValueError("day_scores must include at least one day score.")
    normalized: list[dict[str, Any]] = []
    seen_day_indexes: set[int] = set()
    for idx, entry in enumerate(day_scores):
        field_path = f"day_scores[{idx}]"
        if not isinstance(entry, Mapping):
            raise ValueError(f"{field_path} must be an object.")
        day_index = coerce_day_index(
            entry.get("day_index"), field_path=f"{field_path}.day_index"
        )
        if day_index in seen_day_indexes:
            raise ValueError(
                f"day_scores contains duplicate day_index values: {day_index}"
            )
        seen_day_indexes.add(day_index)
        normalized.append(
            {
                "day_index": day_index,
                "score": coerce_score(
                    entry.get("score"), field_path=f"{field_path}.score"
                ),
                "rubric_results_json": coerce_rubric_results_json(
                    entry.get("rubric_results_json"),
                    field_path=f"{field_path}.rubric_results_json",
                ),
                "evidence_pointers_json": validate_evidence_pointers(
                    entry.get("evidence_pointers_json")
                ),
            }
        )
    return normalized


async def add_day_scores(
    db: AsyncSession,
    *,
    run: EvaluationRun,
    day_scores: Sequence[Mapping[str, Any]],
    allow_empty: bool = False,
    commit: bool = True,
) -> list[EvaluationDayScore]:
    """Add day scores."""
    if run.id is None:
        raise ValueError("run must be persisted before adding day scores.")
    normalized_entries = normalize_day_score_payload(
        day_scores, allow_empty=allow_empty
    )
    if not normalized_entries:
        await (db.commit() if commit else db.flush())
        return []
    existing_day_indexes = set(
        (
            await db.execute(
                select(EvaluationDayScore.day_index).where(
                    EvaluationDayScore.run_id == run.id
                )
            )
        ).scalars()
    )
    duplicates = sorted(
        {
            int(entry["day_index"])
            for entry in normalized_entries
            if int(entry["day_index"]) in existing_day_indexes
        }
    )
    if duplicates:
        joined = ", ".join(str(value) for value in duplicates)
        raise ValueError(f"run already has day scores for day_index values: {joined}")
    created: list[EvaluationDayScore] = []
    for entry in normalized_entries:
        day_score = EvaluationDayScore(
            run=run,
            day_index=int(entry["day_index"]),
            score=float(entry["score"]),
            rubric_results_json=dict(entry["rubric_results_json"]),
            evidence_pointers_json=list(entry["evidence_pointers_json"]),
        )
        created.append(day_score)
        db.add(day_score)
    if commit:
        await db.commit()
        for row in created:
            await db.refresh(row)
    else:
        await db.flush()
    return created
