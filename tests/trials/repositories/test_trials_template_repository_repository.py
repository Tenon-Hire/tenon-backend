from app.trials.services import _template_repo_for_task
from tests.shared.factories import create_talent_partner, create_trial


async def test_template_repo_mapping_code_and_debug(async_session):
    expected = "winoe-hire-dev/winoe-template-python-fastapi"
    assert _template_repo_for_task(2, "code", "python-fastapi") == expected
    assert _template_repo_for_task(3, "debug", "python-fastapi") == expected


async def test_create_trial_sets_template_repo(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="template-map@sim.com"
    )
    _sim, tasks = await create_trial(async_session, created_by=talent_partner)
    for task in tasks:
        if task.type in {"code", "debug"}:
            assert task.template_repo
