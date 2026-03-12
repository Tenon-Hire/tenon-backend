import pytest

from app.domains import Company, User
from app.domains.simulations.ai_config import AI_NOTICE_DEFAULT_TEXT


@pytest.mark.asyncio
async def test_update_simulation_ai_partial_merge(
    async_client, async_session, auth_header_factory
):
    company = Company(name="UpdateCo")
    async_session.add(company)
    await async_session.flush()

    recruiter = User(
        name="Recruiter Update",
        email="recruiter-update@acme.com",
        role="recruiter",
        company_id=company.id,
        password_hash=None,
    )
    async_session.add(recruiter)
    await async_session.commit()

    create_res = await async_client.post(
        "/api/simulations",
        headers=auth_header_factory(recruiter),
        json={
            "title": "Sim Update",
            "role": "Backend Engineer",
            "techStack": "Python",
            "seniority": "Mid",
            "focus": "Update AI controls",
            "ai": {
                "noticeVersion": "mvp1",
                "noticeText": "Initial notice text",
                "evalEnabledByDay": {
                    "1": True,
                    "2": True,
                    "3": True,
                    "4": False,
                    "5": True,
                },
            },
        },
    )
    assert create_res.status_code == 201, create_res.text
    simulation_id = create_res.json()["id"]

    update_res = await async_client.put(
        f"/api/simulations/{simulation_id}",
        headers=auth_header_factory(recruiter),
        json={
            "ai": {
                "noticeVersion": "mvp2",
                "evalEnabledByDay": {"2": False},
            }
        },
    )
    assert update_res.status_code == 200, update_res.text
    body = update_res.json()
    assert body["id"] == simulation_id
    assert body["ai"]["noticeVersion"] == "mvp2"
    assert body["ai"]["noticeText"] == "Initial notice text"
    assert body["ai"]["evalEnabledByDay"] == {
        "1": True,
        "2": False,
        "3": True,
        "4": False,
        "5": True,
    }


@pytest.mark.asyncio
async def test_update_simulation_omitted_ai_preserves_existing(
    async_client, async_session, auth_header_factory
):
    company = Company(name="PreserveCo")
    async_session.add(company)
    await async_session.flush()

    recruiter = User(
        name="Recruiter Preserve",
        email="recruiter-preserve@acme.com",
        role="recruiter",
        company_id=company.id,
        password_hash=None,
    )
    async_session.add(recruiter)
    await async_session.commit()

    create_res = await async_client.post(
        "/api/simulations",
        headers=auth_header_factory(recruiter),
        json={
            "title": "Sim Preserve",
            "role": "Backend Engineer",
            "techStack": "Python",
            "seniority": "Mid",
            "focus": "No-op AI update",
            "ai": {
                "noticeVersion": "mvp9",
                "noticeText": "Custom notice",
                "evalEnabledByDay": {
                    "1": True,
                    "2": False,
                    "3": True,
                    "4": True,
                    "5": False,
                },
            },
        },
    )
    assert create_res.status_code == 201, create_res.text
    simulation_id = create_res.json()["id"]

    update_res = await async_client.put(
        f"/api/simulations/{simulation_id}",
        headers=auth_header_factory(recruiter),
        json={},
    )
    assert update_res.status_code == 200, update_res.text
    body = update_res.json()
    assert body["ai"] == {
        "noticeVersion": "mvp9",
        "noticeText": "Custom notice",
        "evalEnabledByDay": {
            "1": True,
            "2": False,
            "3": True,
            "4": True,
            "5": False,
        },
    }


@pytest.mark.asyncio
async def test_update_simulation_forbidden_for_non_recruiter(
    async_client, async_session, auth_header_factory
):
    company = Company(name="ForbiddenCo")
    async_session.add(company)
    await async_session.flush()

    recruiter = User(
        name="Recruiter Owner",
        email="recruiter-owner@acme.com",
        role="recruiter",
        company_id=company.id,
        password_hash=None,
    )
    candidate = User(
        name="Candidate User",
        email="candidate-user@acme.com",
        role="candidate",
        company_id=company.id,
        password_hash=None,
    )
    async_session.add_all([recruiter, candidate])
    await async_session.commit()

    create_res = await async_client.post(
        "/api/simulations",
        headers=auth_header_factory(recruiter),
        json={
            "title": "Sim Forbidden",
            "role": "Backend Engineer",
            "techStack": "Python",
            "seniority": "Mid",
            "focus": "Forbidden updates",
        },
    )
    assert create_res.status_code == 201, create_res.text
    simulation_id = create_res.json()["id"]

    update_res = await async_client.put(
        f"/api/simulations/{simulation_id}",
        headers=auth_header_factory(candidate),
        json={
            "ai": {
                "noticeVersion": "mvp2",
                "noticeText": AI_NOTICE_DEFAULT_TEXT,
                "evalEnabledByDay": {"1": False},
            }
        },
    )
    assert update_res.status_code == 403, update_res.text


@pytest.mark.asyncio
async def test_update_simulation_rejects_invalid_ai_day_key(
    async_client, async_session, auth_header_factory
):
    company = Company(name="InvalidAiUpdateCo")
    async_session.add(company)
    await async_session.flush()

    recruiter = User(
        name="Recruiter Invalid Update",
        email="recruiter-invalid-update@acme.com",
        role="recruiter",
        company_id=company.id,
        password_hash=None,
    )
    async_session.add(recruiter)
    await async_session.commit()

    create_res = await async_client.post(
        "/api/simulations",
        headers=auth_header_factory(recruiter),
        json={
            "title": "Sim Invalid Update",
            "role": "Backend Engineer",
            "techStack": "Python",
            "seniority": "Mid",
            "focus": "Invalid AI update",
        },
    )
    assert create_res.status_code == 201, create_res.text
    simulation_id = create_res.json()["id"]

    update_res = await async_client.put(
        f"/api/simulations/{simulation_id}",
        headers=auth_header_factory(recruiter),
        json={"ai": {"evalEnabledByDay": {"6": True}}},
    )
    assert update_res.status_code == 422, update_res.text
