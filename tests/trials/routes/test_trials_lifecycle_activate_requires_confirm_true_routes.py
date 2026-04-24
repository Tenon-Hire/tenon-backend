from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.ai import AIPolicySnapshotError
from app.shared.utils.shared_utils_errors_utils import ApiError
from app.trials.routes.trials_routes import lifecycle as lifecycle_route
from tests.trials.routes.trials_lifecycle_api_utils import *
from tests.trials.routes.trials_scenario_versions_api_utils import _approve_trial


@pytest.mark.asyncio
async def test_activate_requires_confirm_true(
    async_client, async_session, auth_header_factory
):
    owner = await create_talent_partner(
        async_session, email="confirm-lifecycle@test.com"
    )
    created = await _create_trial_via_api(
        async_client, async_session, auth_header_factory(owner)
    )
    sim_id = created["id"]
    await _approve_trial(
        async_client, sim_id=sim_id, headers=auth_header_factory(owner)
    )

    res = await async_client.post(
        f"/api/trials/{sim_id}/activate",
        headers=auth_header_factory(owner),
        json={"confirm": False},
    )
    assert res.status_code == 400
    assert res.json()["errorCode"] == "TRIAL_CONFIRMATION_REQUIRED"


@pytest.mark.asyncio
async def test_activate_maps_snapshot_validation_error(monkeypatch):
    monkeypatch.setattr(
        lifecycle_route, "ensure_talent_partner_or_none", lambda _u: None
    )

    async def fake_activate(*_args, **_kwargs):
        raise AIPolicySnapshotError("boom")

    monkeypatch.setattr(lifecycle_route.sim_service, "activate_trial", fake_activate)

    with pytest.raises(ApiError) as excinfo:
        await lifecycle_route.activate_trial(
            trial_id=1,
            payload=SimpleNamespace(confirm=True, reason=None),
            db=object(),
            user=SimpleNamespace(id=7, role="talent_partner"),
        )
    assert excinfo.value.status_code == 409
    assert excinfo.value.error_code == "scenario_version_ai_policy_snapshot_invalid"
