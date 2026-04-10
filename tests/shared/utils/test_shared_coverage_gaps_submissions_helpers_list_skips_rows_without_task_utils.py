from __future__ import annotations

import pytest

from tests.shared.utils.shared_coverage_gaps_utils import *


@pytest.mark.asyncio
async def test_submissions_helpers_list_skips_rows_without_task(monkeypatch):
    async def _fake_list(*_a, **_k):
        return [object(), ("sub", None), ("sub", "task")]

    monkeypatch.setattr(
        submissions_helpers, "ensure_talent_partner_guard", lambda _u: None
    )
    monkeypatch.setattr(
        submissions_helpers.talent_partner_sub_service, "list_submissions", _fake_list
    )
    monkeypatch.setattr(
        submissions_helpers,
        "present_list_item",
        lambda *_a, **_k: {
            "submissionId": 1,
            "candidateSessionId": 2,
            "taskId": 3,
            "dayIndex": 1,
            "type": "code",
            "submittedAt": datetime.now(UTC),
        },
    )
    result = await submissions_helpers.list_submissions(
        db=object(),
        user=SimpleNamespace(id=7),
    )
    assert len(result.items) == 1
