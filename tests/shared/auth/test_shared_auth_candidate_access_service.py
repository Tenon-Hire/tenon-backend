import pytest

from app.shared.auth import shared_auth_candidate_access_utils as candidate_access
from app.shared.auth.principal import Principal


@pytest.mark.asyncio
async def test_require_candidate_principal_allows_candidate():
    principal = Principal(
        sub="auth0|cand1",
        email="candidate@example.com",
        name="candidate",
        roles=[],
        permissions=["candidate:access"],
        claims={"sub": "auth0|cand1", "email": "candidate@example.com"},
    )
    result = await candidate_access.require_candidate_principal(principal)
    assert result == principal


@pytest.mark.asyncio
async def test_require_candidate_principal_rejects_missing_permission():
    principal = Principal(
        sub="auth0|talent_partner1",
        email="talent_partner@example.com",
        name="talent_partner",
        roles=[],
        permissions=["talent_partner:access"],
        claims={"sub": "auth0|talent_partner1", "email": "talent_partner@example.com"},
    )
    with pytest.raises(Exception) as excinfo:
        await candidate_access.require_candidate_principal(principal)
    assert excinfo.value.status_code == 403
