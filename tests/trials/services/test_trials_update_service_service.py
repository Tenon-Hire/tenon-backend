from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.trials.services import update as sim_update_service


class _DummyDB:
    def __init__(self) -> None:
        self.commit_calls = 0
        self.refresh_calls: list[object] = []

    async def commit(self) -> None:
        self.commit_calls += 1

    async def refresh(self, instance: object) -> None:
        self.refresh_calls.append(instance)


def test_ai_payload_field_set_handles_non_set_model_fields() -> None:
    ai_payload = SimpleNamespace(model_fields_set=["notice_version"])
    assert sim_update_service._ai_payload_field_set(ai_payload) == set()


@pytest.mark.asyncio
async def test_update_trial_logs_ai_changes_without_notice_text(
    monkeypatch,
    caplog,
):
    existing_notice_text = "Old private notice text"
    incoming_notice_text = "New private notice text that should never be logged"
    trial = SimpleNamespace(
        id=42,
        ai_notice_version="mvp1",
        ai_notice_text=existing_notice_text,
        ai_eval_enabled_by_day={"1": True, "2": True, "3": True, "4": True, "5": True},
    )
    tasks = [SimpleNamespace(id=1), SimpleNamespace(id=2)]

    async def _fake_require_owned_with_tasks(db, trial_id, actor_user_id):
        assert trial_id == 42
        assert actor_user_id == 7
        return trial, tasks

    monkeypatch.setattr(
        sim_update_service,
        "require_owned_trial_with_tasks",
        _fake_require_owned_with_tasks,
    )

    payload = SimpleNamespace(
        ai=SimpleNamespace(
            model_fields_set={"notice_version", "notice_text", "eval_enabled_by_day"},
            notice_version="mvp2",
            notice_text=incoming_notice_text,
            eval_enabled_by_day={
                "1": True,
                "2": False,
                "3": True,
                "4": True,
                "5": False,
            },
        )
    )
    db = _DummyDB()
    caplog.set_level(
        "INFO",
        logger="app.trials.services.trials_services_trials_update_service",
    )

    updated_trial, updated_tasks = await sim_update_service.update_trial(
        db,
        trial_id=42,
        actor_user_id=7,
        payload=payload,
    )

    assert updated_trial is trial
    assert updated_tasks == tasks
    assert trial.ai_notice_version == "mvp2"
    assert trial.ai_notice_text == incoming_notice_text
    assert trial.ai_eval_enabled_by_day == {
        "1": True,
        "2": False,
        "3": True,
        "4": True,
        "5": False,
    }
    assert db.commit_calls == 1
    assert len(db.refresh_calls) == 3

    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert "trial_ai_notice_version_changed trialId=42 actorUserId=7" in log_text
    assert "from=mvp1 to=mvp2" in log_text
    assert "trial_ai_eval_toggles_changed trialId=42 actorUserId=7" in log_text
    assert "changedDays=[2, 5]" in log_text
    assert existing_notice_text not in log_text
    assert incoming_notice_text not in log_text


@pytest.mark.asyncio
async def test_update_trial_without_ai_payload_is_noop(monkeypatch):
    trial = SimpleNamespace(id=55)
    tasks = [SimpleNamespace(id=1)]

    async def _fake_require_owned_with_tasks(db, trial_id, actor_user_id):
        assert trial_id == 55
        assert actor_user_id == 9
        return trial, tasks

    monkeypatch.setattr(
        sim_update_service,
        "require_owned_trial_with_tasks",
        _fake_require_owned_with_tasks,
    )

    db = _DummyDB()
    payload = SimpleNamespace()
    updated_trial, updated_tasks = await sim_update_service.update_trial(
        db,
        trial_id=55,
        actor_user_id=9,
        payload=payload,
    )

    assert updated_trial is trial
    assert updated_tasks == tasks
    assert db.commit_calls == 0
    assert db.refresh_calls == []
