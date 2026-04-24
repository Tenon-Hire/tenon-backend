from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import Request

from app.candidates.routes.candidate_sessions_routes.candidates_routes_candidate_sessions_routes_candidates_candidate_sessions_routes_invites_routes import (
    list_candidate_invites,
)
from app.candidates.routes.candidate_sessions_routes.candidates_routes_candidate_sessions_routes_candidates_candidate_sessions_routes_invites_routes import (
    router as candidate_invites_router,
)


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/candidate/invites",
            "headers": [],
            "query_string": b"",
        }
    )


@pytest.mark.asyncio
async def test_candidate_invites_hide_terminated_by_default(monkeypatch):
    assert candidate_invites_router is not None

    principal = SimpleNamespace(
        sub="candidate-candidate-filter@example.com",
        email="candidate-filter@example.com",
    )
    db = object()
    request = _request()
    service_result = [
        {
            "candidateSessionId": 1,
            "title": "Completed trial",
            "role": "Engineer",
            "companyName": "Acme",
            "status": "completed",
            "progress": {"completed": 5, "total": 5},
            "reportReady": True,
            "hasReport": True,
            "terminatedAt": None,
            "isTerminated": False,
        },
        {
            "candidateSessionId": 2,
            "title": "Terminated trial",
            "role": "Engineer",
            "companyName": "Acme",
            "status": "terminated",
            "progress": {"completed": 5, "total": 5},
            "reportReady": False,
            "hasReport": False,
            "terminatedAt": "2026-03-26T12:00:00Z",
            "isTerminated": True,
        },
    ]
    invite_list_mock = AsyncMock(return_value=service_result)
    monkeypatch.setattr(
        "app.candidates.routes.candidate_sessions_routes.candidates_routes_candidate_sessions_routes_candidates_candidate_sessions_routes_invites_routes.rate_limit.rate_limit_enabled",
        lambda: False,
    )
    monkeypatch.setattr(
        "app.candidates.routes.candidate_sessions_routes.candidates_routes_candidate_sessions_routes_candidates_candidate_sessions_routes_invites_routes.cs_service.invite_list_for_principal",
        invite_list_mock,
    )

    default_rows = await list_candidate_invites(request, principal, db)
    include_terminated_rows = await list_candidate_invites(
        request, principal, db, includeTerminated=True
    )

    assert default_rows == service_result
    assert include_terminated_rows == service_result
    invite_list_mock.assert_any_await(db, principal)
    invite_list_mock.assert_any_await(db, principal, include_terminated=True)
