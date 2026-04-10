from __future__ import annotations

import pytest

from tests.trials.routes.trials_scenario_versions_api_utils import *


@pytest.mark.asyncio
async def test_patch_scenario_version_creates_audit_row_per_successful_edit(
    async_client, async_session, auth_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="scenario-patch-audit-count@test.com"
    )
    headers = auth_header_factory(talent_partner)
    sim_id = await _create_trial(async_client, async_session, headers)

    detail = await async_client.get(f"/api/trials/{sim_id}", headers=headers)
    assert detail.status_code == 200, detail.text
    scenario_version_id = detail.json()["activeScenarioVersionId"]
    assert scenario_version_id is not None

    first = await async_client.patch(
        f"/api/trials/{sim_id}/scenario/{scenario_version_id}",
        headers=headers,
        json={"notes": "First edit"},
    )
    assert first.status_code == 200, first.text

    second = await async_client.patch(
        f"/api/trials/{sim_id}/scenario/{scenario_version_id}",
        headers=headers,
        json={"storylineMd": "## second edit"},
    )
    assert second.status_code == 200, second.text

    audits = (
        (
            await async_session.execute(
                select(ScenarioEditAudit).where(
                    ScenarioEditAudit.scenario_version_id == scenario_version_id
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(audits) == 2
    assert all(audit.talent_partner_id == talent_partner.id for audit in audits)
