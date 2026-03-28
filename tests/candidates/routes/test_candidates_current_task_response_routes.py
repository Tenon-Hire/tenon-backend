from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from app.candidates.routes.candidate_sessions_routes import (
    candidates_routes_candidate_sessions_routes_candidates_candidate_sessions_routes_responses_current_task_routes as current_task_responses,
)


def test_resolve_cutoff_fields_keeps_timezone_aware_datetime():
    aware_cutoff = datetime(2026, 3, 26, 12, 0, tzinfo=UTC)
    day_audit = SimpleNamespace(cutoff_commit_sha="sha-aware", cutoff_at=aware_cutoff)

    cutoff_commit_sha, cutoff_at = current_task_responses._resolve_cutoff_fields(
        day_audit
    )

    assert cutoff_commit_sha == "sha-aware"
    assert cutoff_at is aware_cutoff
