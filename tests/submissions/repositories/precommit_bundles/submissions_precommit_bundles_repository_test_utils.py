from __future__ import annotations

import json

from tests.shared.factories import create_recruiter, create_simulation


def patch_body(path: str, content: str) -> str:
    return json.dumps({"files": [{"path": path, "content": content}]})


async def seed_bundle_context(async_session, *, email: str):
    recruiter = await create_recruiter(async_session, email=email)
    sim, _tasks = await create_simulation(async_session, created_by=recruiter)
    scenario_version_id = sim.active_scenario_version_id
    assert scenario_version_id is not None
    return sim, scenario_version_id
