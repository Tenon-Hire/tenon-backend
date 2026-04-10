import pytest

from app.shared.auth.shared_auth_current_user_utils import get_current_user
from app.shared.database.shared_database_models_model import Company, User


@pytest.mark.asyncio
async def test_list_trials_does_not_show_other_users(authed_client, async_session):
    other_company = Company(name="OtherCo")
    async_session.add(other_company)
    await async_session.flush()
    other_user = User(
        name="TalentPartner Two",
        email="other@test.com",
        role="talent_partner",
        company_id=other_company.id,
        password_hash=None,
    )
    async_session.add(other_user)
    await async_session.flush()
    from app.trials.repositories.trials_repositories_trials_trial_model import (
        Trial,
    )

    other_sim = Trial(
        title="Other User Sim",
        role="Backend Engineer",
        tech_stack="Node.js, PostgreSQL",
        seniority="Mid",
        focus="Should not appear",
        scenario_template="default-5day-node-postgres",
        company_id=other_company.id,
        created_by=other_user.id,
    )
    async_session.add(other_sim)
    await async_session.commit()

    resp = await authed_client.get("/api/trials")
    assert resp.status_code == 200
    titles = {x["title"] for x in resp.json()}
    assert "Other User Sim" not in titles


@pytest.mark.asyncio
async def test_list_trials_forbidden_for_non_talent_partner(
    async_client, async_session, override_dependencies
):
    company = Company(name="CandidateCo")
    async_session.add(company)
    await async_session.flush()
    candidate_user = User(
        name="Candidate User",
        email="candidate@test.com",
        role="candidate",
        company_id=company.id,
        password_hash=None,
    )
    async_session.add(candidate_user)
    await async_session.commit()

    with override_dependencies({get_current_user: lambda: candidate_user}):
        resp = await async_client.get("/api/trials")
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Talent Partner access required"
