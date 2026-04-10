from __future__ import annotations

import json

from tests.shared.factories import create_talent_partner, create_trial


def patch_body(path: str, content: str) -> str:
    return json.dumps({"files": [{"path": path, "content": content}]})


async def seed_bundle_context(async_session, *, email: str):
    talent_partner = await create_talent_partner(async_session, email=email)
    sim, _tasks = await create_trial(async_session, created_by=talent_partner)
    scenario_version_id = sim.active_scenario_version_id
    assert scenario_version_id is not None
    return sim, scenario_version_id
