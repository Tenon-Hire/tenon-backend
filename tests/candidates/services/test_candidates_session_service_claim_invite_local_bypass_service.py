from __future__ import annotations

import pytest

from tests.candidates.services.candidates_session_service_utils import *


@pytest.mark.asyncio
async def test_claim_invite_rejects_unverified_email_even_in_local_env(
    async_session, monkeypatch
):
    monkeypatch.setattr(settings, "ENV", "local")
    talent_partner = await create_talent_partner(
        async_session, email="local-bypass@sim.com"
    )
    sim, _ = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(async_session, trial=sim)
    principal = _principal(cs.invite_email, email_verified=False)

    with pytest.raises(HTTPException) as excinfo:
        await cs_service.claim_invite_with_principal(async_session, cs.token, principal)

    assert excinfo.value.status_code == 403
    assert getattr(excinfo.value, "error_code", None) == "CANDIDATE_EMAIL_NOT_VERIFIED"
