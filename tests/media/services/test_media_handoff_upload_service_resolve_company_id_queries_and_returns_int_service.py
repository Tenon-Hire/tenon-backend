from __future__ import annotations

import pytest

from tests.media.services.media_handoff_upload_service_utils import *


@pytest.mark.asyncio
async def test_resolve_company_id_queries_and_returns_int(async_session):
    task, _, candidate_session = await _setup_handoff_context(
        async_session,
        "service-company-query@test.com",
    )
    candidate_session.__dict__.pop("trial", None)

    resolved = await _resolve_company_id(
        async_session,
        candidate_session=candidate_session,
        trial_id=task.trial_id,
    )
    assert isinstance(resolved, int)
