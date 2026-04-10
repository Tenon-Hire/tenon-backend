from __future__ import annotations

import pytest
from sqlalchemy import select

from app.shared.database.shared_database_models_model import Company
from tests.trials.routes.trials_api_utils import *


@pytest.mark.asyncio
async def test_company_ai_config_round_trips_prompt_overrides(
    async_client, async_session, auth_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="company-ai@test.com"
    )
    headers = auth_header_factory(talent_partner)

    initial = await async_client.get("/api/companies/me/ai-config", headers=headers)
    assert initial.status_code == 200, initial.text
    assert initial.json()["promptOverrides"] is None

    update = await async_client.put(
        "/api/companies/me/ai-config",
        headers=headers,
        json={
            "promptOverrides": {
                "prestart": {"instructionsMd": "Use Acme platform language."},
                "day23": {"rubricMd": "Prefer test-first and debugging depth."},
            }
        },
    )
    assert update.status_code == 200, update.text
    body = update.json()
    assert body["companyId"] == talent_partner.company_id
    assert body["promptOverrides"]["prestart"]["instructionsMd"] == (
        "Use Acme platform language."
    )
    assert body["promptOverrides"]["day23"]["rubricMd"] == (
        "Prefer test-first and debugging depth."
    )

    company = await async_session.scalar(
        select(Company).where(Company.id == talent_partner.company_id)
    )
    assert company is not None
    assert company.ai_prompt_overrides_json == body["promptOverrides"]


@pytest.mark.asyncio
async def test_company_ai_config_put_can_clear_prompt_overrides(
    async_client, async_session, auth_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="company-ai-clear@test.com"
    )
    headers = auth_header_factory(talent_partner)

    seeded = await async_session.scalar(
        select(Company).where(Company.id == talent_partner.company_id)
    )
    seeded.ai_prompt_overrides_json = {
        "winoeReport": {"rubricMd": "Keep prior override"}
    }
    await async_session.commit()

    cleared = await async_client.put(
        "/api/companies/me/ai-config",
        headers=headers,
        json={"promptOverrides": None},
    )
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["promptOverrides"] is None

    company = await async_session.scalar(
        select(Company).where(Company.id == talent_partner.company_id)
    )
    assert company is not None
    assert company.ai_prompt_overrides_json is None
