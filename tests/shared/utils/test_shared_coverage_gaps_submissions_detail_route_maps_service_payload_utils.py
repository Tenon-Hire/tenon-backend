from __future__ import annotations

import pytest

from tests.shared.utils.shared_coverage_gaps_utils import *


@pytest.mark.asyncio
async def test_submissions_detail_route_maps_service_payload(monkeypatch):
    async def _fake_fetch_detail(*_a, **_k):
        return object(), object(), object(), object()

    monkeypatch.setattr(
        submissions_detail_route, "ensure_talent_partner", lambda _u: None
    )
    monkeypatch.setattr(
        submissions_detail_route.talent_partner_sub_service,
        "fetch_detail",
        _fake_fetch_detail,
    )
    monkeypatch.setattr(
        submissions_detail_route,
        "present_detail",
        lambda *_a, **_k: {
            "submissionId": 1,
            "candidateSessionId": 2,
            "task": {"taskId": 3, "dayIndex": 1, "type": "code"},
            "submittedAt": datetime.now(UTC),
        },
    )
    result = await submissions_detail_route.get_submission_detail_route(
        submission_id=123,
        db=object(),
        user=SimpleNamespace(id=99),
    )
    assert result.submissionId == 1
