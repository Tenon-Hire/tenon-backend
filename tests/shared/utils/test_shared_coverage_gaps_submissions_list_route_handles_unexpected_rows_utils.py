from __future__ import annotations

import pytest

from tests.shared.utils.shared_coverage_gaps_utils import *


@pytest.mark.asyncio
async def test_submissions_list_route_handles_unexpected_rows(monkeypatch):
    async def _fake_list(*_a, **_k):
        return [object(), ("sub", "task"), ("sub", None), ("sub", "task", "extra")]

    monkeypatch.setattr(
        submissions_list_route, "ensure_talent_partner", lambda _u: None
    )
    monkeypatch.setattr(
        submissions_list_route.talent_partner_sub_service,
        "list_submissions",
        _fake_list,
    )
    monkeypatch.setattr(
        submissions_list_route,
        "present_list_item",
        lambda _sub, _task: {
            "submissionId": 1,
            "candidateSessionId": 2,
            "taskId": 3,
            "dayIndex": 1,
            "type": "code",
            "submittedAt": datetime.now(UTC),
        },
    )
    result = await submissions_list_route.list_submissions_route(
        db=object(),
        user=SimpleNamespace(id=7),
    )
    assert len(result.items) == 2
