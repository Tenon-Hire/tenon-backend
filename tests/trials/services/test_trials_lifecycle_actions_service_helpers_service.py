from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.shared.utils.shared_utils_errors_utils import ApiError
from app.trials.repositories.trials_repositories_trials_trial_model import (
    TRIAL_STATUS_ACTIVE_INVITING,
)
from app.trials.services import (
    trials_services_trials_lifecycle_actions_service as lifecycle_actions_service,
)
from app.trials.services import (
    trials_services_trials_lifecycle_service as lifecycle_service,
)
from app.trials.services import (
    trials_services_trials_scenario_versions_approval_service as approval_service,
)
from tests.shared.factories import create_talent_partner, create_trial


@pytest.mark.asyncio
async def test_transition_owned_trial_impl_rejects_pending_invite():
    trial = SimpleNamespace(
        id=1,
        status="ready",
        pending_scenario_version_id=42,
    )

    async def fake_require_owner(*_args, **_kwargs):
        return trial

    with pytest.raises(ApiError) as excinfo:
        await lifecycle_actions_service._transition_owned_trial_impl(
            SimpleNamespace(commit=None, refresh=None),
            trial_id=trial.id,
            actor_user_id=7,
            target_status=TRIAL_STATUS_ACTIVE_INVITING,
            require_owner=fake_require_owner,
            apply_transition=lambda *_args, **_kwargs: True,
            normalize_status=lambda value: value,
            logger=SimpleNamespace(
                info=lambda *_a, **_k: None, warning=lambda *_a, **_k: None
            ),
        )
    assert excinfo.value.status_code == 409
    assert excinfo.value.error_code == "SCENARIO_APPROVAL_PENDING"


@pytest.mark.asyncio
async def test_transition_owned_trial_impl_success_and_load_trial_tasks(async_session):
    owner = await create_talent_partner(
        async_session, email="lifecycle-actions-helper@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=owner)
    trial = SimpleNamespace(
        id=sim.id,
        status="ready",
        pending_scenario_version_id=None,
    )
    commit_calls = []
    refresh_calls = []

    class FakeDB:
        async def commit(self):
            commit_calls.append("commit")

        async def refresh(self, obj):
            refresh_calls.append(getattr(obj, "id", None))

    async def fake_require_owner(*_args, **_kwargs):
        return trial

    def fake_apply_transition(trial_obj, *, target_status, changed_at):
        trial_obj.status = target_status
        return True

    logger = SimpleNamespace(
        info=lambda *_a, **_k: None, warning=lambda *_a, **_k: None
    )
    updated_trial = await lifecycle_actions_service._transition_owned_trial_impl(
        FakeDB(),
        trial_id=trial.id,
        actor_user_id=owner.id,
        target_status=TRIAL_STATUS_ACTIVE_INVITING,
        require_owner=fake_require_owner,
        apply_transition=fake_apply_transition,
        normalize_status=lambda value: value,
        logger=logger,
    )
    assert updated_trial.status == TRIAL_STATUS_ACTIVE_INVITING
    assert commit_calls == ["commit"]
    assert refresh_calls == [trial.id]

    lifecycle_loaded = await lifecycle_service._load_trial_tasks(async_session, sim.id)
    approval_loaded = await approval_service._load_trial_tasks(async_session, sim.id)
    expected = sorted(task.day_index for task in tasks)
    assert [task.day_index for task in lifecycle_loaded] == expected
    assert [task.day_index for task in approval_loaded] == expected


@pytest.mark.asyncio
async def test_transition_owned_trial_impl_logs_and_re_raises_api_error():
    trial = SimpleNamespace(
        id=1,
        status="ready",
        pending_scenario_version_id=None,
    )
    commit_calls = []
    refresh_calls = []
    warnings = []

    class FakeDB:
        async def commit(self):
            commit_calls.append("commit")

        async def refresh(self, obj):
            refresh_calls.append(getattr(obj, "id", None))

    async def fake_require_owner(*_args, **_kwargs):
        return trial

    def fake_apply_transition(*_args, **_kwargs):
        raise ApiError(
            status_code=400,
            detail="transition rejected",
            error_code="TRANSITION_REJECTED",
            retryable=False,
        )

    logger = SimpleNamespace(
        info=lambda *_a, **_k: None,
        warning=lambda *args, **_kwargs: warnings.append(args),
    )

    with pytest.raises(ApiError):
        await lifecycle_actions_service._transition_owned_trial_impl(
            FakeDB(),
            trial_id=trial.id,
            actor_user_id=7,
            target_status="active_inviting",
            require_owner=fake_require_owner,
            apply_transition=fake_apply_transition,
            normalize_status=lambda value: value,
            logger=logger,
        )

    assert commit_calls == []
    assert refresh_calls == []
    assert warnings


@pytest.mark.asyncio
async def test_transition_owned_trial_impl_idempotent_path_logs_without_change():
    trial = SimpleNamespace(
        id=2,
        status="ready",
        pending_scenario_version_id=None,
    )
    commit_calls = []
    refresh_calls = []
    infos = []

    class FakeDB:
        async def commit(self):
            commit_calls.append("commit")

        async def refresh(self, obj):
            refresh_calls.append(getattr(obj, "id", None))

    async def fake_require_owner(*_args, **_kwargs):
        return trial

    def fake_apply_transition(*_args, **_kwargs):
        return False

    logger = SimpleNamespace(
        info=lambda *args, **_kwargs: infos.append(args),
        warning=lambda *_a, **_k: None,
    )

    updated_trial = await lifecycle_actions_service._transition_owned_trial_impl(
        FakeDB(),
        trial_id=trial.id,
        actor_user_id=7,
        target_status="ready",
        require_owner=fake_require_owner,
        apply_transition=fake_apply_transition,
        normalize_status=lambda value: value,
        logger=logger,
    )

    assert updated_trial is trial
    assert commit_calls == ["commit"]
    assert refresh_calls == [trial.id]
    assert infos
