from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.submissions.routes.submissions_routes import (
    submissions_routes_submissions_routes_submissions_routes_list_routes as list_routes,
)


def _list_payload(*, submission_id: int) -> dict[str, object]:
    return {
        "submissionId": submission_id,
        "candidateSessionId": 10,
        "taskId": 100 + submission_id,
        "dayIndex": 1,
        "type": "code",
        "submittedAt": datetime(2026, 3, 20, 12, 0, tzinfo=UTC),
        "repoFullName": None,
        "repoUrl": None,
        "workflowRunId": None,
        "commitSha": None,
        "cutoffCommitSha": None,
        "cutoffAt": None,
        "evalBasisRef": None,
        "workflowUrl": None,
        "commitUrl": None,
        "diffUrl": None,
        "diffSummary": None,
        "testResults": None,
    }


@pytest.mark.asyncio
async def test_list_submissions_route_filters_day_audit_lookup_inputs(monkeypatch):
    row_with_valid_day = (
        SimpleNamespace(id=1, candidate_session_id=10, task_id=101),
        SimpleNamespace(day_index=2, type="code"),
    )
    row_with_invalid_day = (
        SimpleNamespace(id=2, candidate_session_id=10, task_id=102),
        SimpleNamespace(day_index="not-an-int", type="code"),
    )
    rows = [row_with_valid_day, row_with_invalid_day, object(), (object(),)]
    captured_lookup: dict[str, set[int]] = {}
    seen_day_audits: dict[int, object | None] = {}

    monkeypatch.setattr(list_routes, "ensure_talent_partner", lambda _user: None)

    async def _list_submissions(*_args, **_kwargs):
        return rows

    async def _list_day_audits(_db, *, candidate_session_ids, day_indexes):
        captured_lookup["candidate_session_ids"] = set(candidate_session_ids)
        captured_lookup["day_indexes"] = set(day_indexes)
        return [
            SimpleNamespace(
                candidate_session_id=10,
                day_index=2,
                eval_basis_ref="audit-ref",
            )
        ]

    def _present_list_item(sub, _task, *, day_audit=None):
        seen_day_audits[sub.id] = day_audit
        payload = _list_payload(submission_id=sub.id)
        if day_audit is not None:
            payload["evalBasisRef"] = day_audit.eval_basis_ref
        return payload

    monkeypatch.setattr(
        list_routes.talent_partner_sub_service, "list_submissions", _list_submissions
    )
    monkeypatch.setattr(list_routes.cs_repo, "list_day_audits", _list_day_audits)
    monkeypatch.setattr(list_routes, "present_list_item", _present_list_item)

    response = await list_routes.list_submissions_route(
        db=object(),
        user=SimpleNamespace(id=7),
        candidateSessionId=None,
        taskId=None,
        limit=None,
        offset=0,
    )

    assert captured_lookup["candidate_session_ids"] == {10}
    assert captured_lookup["day_indexes"] == {2}
    assert seen_day_audits[1] is not None
    assert seen_day_audits[2] is None
    assert len(response.items) == 2
    assert response.items[0].submissionId == 1
    assert response.items[0].evalBasisRef == "audit-ref"


@pytest.mark.asyncio
async def test_list_submissions_route_falls_back_when_presenter_rejects_day_audit_kwarg(
    monkeypatch,
):
    rows = [
        (
            SimpleNamespace(id=3, candidate_session_id=10, task_id=103),
            SimpleNamespace(day_index=1, type="code"),
        )
    ]
    presenter_calls = {"count": 0}

    monkeypatch.setattr(list_routes, "ensure_talent_partner", lambda _user: None)

    async def _list_submissions(*_args, **_kwargs):
        return rows

    async def _list_day_audits(*_args, **_kwargs):
        return []

    def _present_list_item_without_day_audit(_sub, _task):
        presenter_calls["count"] += 1
        return _list_payload(submission_id=3)

    monkeypatch.setattr(
        list_routes.talent_partner_sub_service, "list_submissions", _list_submissions
    )
    monkeypatch.setattr(list_routes.cs_repo, "list_day_audits", _list_day_audits)
    monkeypatch.setattr(
        list_routes, "present_list_item", _present_list_item_without_day_audit
    )

    response = await list_routes.list_submissions_route(
        db=object(),
        user=SimpleNamespace(id=8),
        candidateSessionId=None,
        taskId=None,
        limit=None,
        offset=0,
    )

    assert presenter_calls["count"] == 1
    assert len(response.items) == 1
    assert response.items[0].submissionId == 3
