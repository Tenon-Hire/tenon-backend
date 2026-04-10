from __future__ import annotations

import pytest

from tests.media.services.media_handoff_upload_service_utils import *


@pytest.mark.asyncio
async def test_resolve_company_id_uses_loaded_trial_company_id(async_session):
    task, _, candidate_session = await _setup_handoff_context(
        async_session,
        "service-company-loaded@test.com",
    )
    candidate_session.__dict__["trial"] = SimpleNamespace(company_id=1234)

    resolved = await _resolve_company_id(
        async_session,
        candidate_session=candidate_session,
        trial_id=task.trial_id,
    )
    assert resolved == 1234
