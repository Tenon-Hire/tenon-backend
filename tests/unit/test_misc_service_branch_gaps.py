"""
GAP-FILLING TESTS: mixed service branch gaps

Targets:
- app/services/{notifications,email,media,simulations,evaluations} branch paths
- Focused on deterministic helper branches and non-happy-path service behavior
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.integrations.notifications.email_provider import EmailSendError
from app.services.evaluations import fit_profile_composer
from app.services.evaluations import runs as evaluation_runs
from app.services.media import keys as media_keys
from app.services.media import privacy as media_privacy
from app.services.notifications.email_sender import EmailSender
from app.services.simulations import (
    candidates_compare,
    invite_factory,
    scenario_payload_builder,
)
from app.services.simulations import update as simulations_update


class _DummyDB:
    def __init__(self):
        self.commits = 0
        self.refreshes = 0
        self.flushes = 0
        self.rollbacks = 0

    async def commit(self):
        self.commits += 1

    async def refresh(self, _obj):
        self.refreshes += 1

    async def flush(self):
        self.flushes += 1

    async def rollback(self):
        self.rollbacks += 1


def test_resolve_create_invite_callable_falls_back_when_service_callable_missing(
    monkeypatch,
):
    from app.domains.simulations import service as simulations_service
    from app.services.simulations.invite_create import create_invite

    monkeypatch.setattr(simulations_service, "create_invite", None, raising=False)

    resolved = invite_factory.resolve_create_invite_callable()

    assert resolved is create_invite


@pytest.mark.asyncio
async def test_email_sender_returns_failed_after_retryable_exhaustion(monkeypatch):
    calls = {"count": 0}

    class _Provider:
        async def send(self, _message):
            calls["count"] += 1
            raise EmailSendError("temporary", retryable=True)

    async def _no_sleep(_seconds):
        return None

    monkeypatch.setattr(asyncio, "sleep", _no_sleep)
    sender = EmailSender(_Provider(), sender="noreply@tenon.ai", max_attempts=2)

    result = await sender.send_email(
        to="candidate@example.com",
        subject="subject",
        text="body",
    )

    assert result.status == "failed"
    assert calls["count"] == 2


@pytest.mark.asyncio
async def test_email_sender_returns_failed_when_attempt_loop_is_empty():
    class _Provider:
        async def send(self, _message):
            raise AssertionError("provider.send should not be called")

    sender = EmailSender(_Provider(), sender="noreply@tenon.ai", max_attempts=1)
    sender.max_attempts = 0

    result = await sender.send_email(
        to="candidate@example.com",
        subject="subject",
        text="body",
    )

    assert result.status == "failed"
    assert result.error == "Email send failed"


def test_parse_recording_public_id_rejects_zero_digit_form():
    with pytest.raises(ValueError, match="recordingId"):
        media_keys.parse_recording_public_id("0")


@pytest.mark.asyncio
async def test_delete_recording_asset_without_transcript_skips_transcript_mark(
    monkeypatch,
):
    db = _DummyDB()
    candidate_session = SimpleNamespace(id=55)
    recording = SimpleNamespace(id=10, candidate_session_id=55, storage_key="k")
    calls = {"mark_transcript_deleted": 0}

    async def _get_by_id_for_update(_db, _recording_id):
        return recording

    async def _mark_deleted(_db, *, recording, now, commit):
        assert recording.id == 10
        assert commit is False

    async def _get_transcript_by_recording_id(_db, _recording_id, include_deleted):
        assert include_deleted is True
        return None

    async def _mark_transcript_deleted(*_args, **_kwargs):
        calls["mark_transcript_deleted"] += 1

    monkeypatch.setattr(
        media_privacy.settings.storage_media, "MEDIA_DELETE_ENABLED", True
    )
    monkeypatch.setattr(
        media_privacy.recordings_repo, "get_by_id_for_update", _get_by_id_for_update
    )
    monkeypatch.setattr(media_privacy.recordings_repo, "mark_deleted", _mark_deleted)
    monkeypatch.setattr(
        media_privacy.transcripts_repo,
        "get_by_recording_id",
        _get_transcript_by_recording_id,
    )
    monkeypatch.setattr(
        media_privacy.transcripts_repo,
        "mark_deleted",
        _mark_transcript_deleted,
    )

    result = await media_privacy.delete_recording_asset(
        db,
        recording_id=10,
        candidate_session=candidate_session,
    )

    assert result is recording
    assert calls["mark_transcript_deleted"] == 0
    assert db.commits == 1
    assert db.refreshes == 1


def test_display_name_falls_back_for_blank_candidate_name():
    resolved = candidates_compare._display_name("   ", position=27)
    assert resolved == "Candidate AB"


def test_display_name_falls_back_for_non_string_candidate_name():
    resolved = candidates_compare._display_name(None, position=0)
    assert resolved == "Candidate A"


def test_build_scenario_generation_payload_omits_optional_recruiter_context(
    monkeypatch,
):
    simulation = SimpleNamespace(
        id=1,
        template_key="python-fastapi",
        scenario_template="backend",
        seniority=None,
        focus=None,
        company_context=None,
        ai_notice_version=None,
        ai_notice_text=None,
        ai_eval_enabled_by_day=None,
    )

    monkeypatch.setattr(
        scenario_payload_builder, "normalize_role_level", lambda _value: None
    )
    monkeypatch.setattr(
        scenario_payload_builder,
        "build_simulation_company_context",
        lambda _value: None,
    )
    monkeypatch.setattr(
        scenario_payload_builder,
        "build_simulation_ai_config",
        lambda **_kwargs: None,
    )

    payload = scenario_payload_builder.build_scenario_generation_payload(simulation)

    assert payload["simulationId"] == 1
    assert payload["recruiterContext"] == {}


def test_sanitize_evidence_handles_missing_ref_and_negative_transcript_end():
    # Covers missing ref branch.
    sanitized_no_ref = fit_profile_composer._sanitize_evidence(
        {"kind": "commit", "ref": 123}
    )
    assert sanitized_no_ref == {"kind": "commit"}

    # Covers transcript endMs rejected branch.
    sanitized_transcript = fit_profile_composer._sanitize_evidence(
        {"kind": "transcript", "startMs": 0, "endMs": -1}
    )
    assert sanitized_transcript == {"kind": "transcript", "startMs": 0}


@pytest.mark.asyncio
async def test_fail_run_allows_metadata_and_error_message_omitted(monkeypatch):
    now = datetime.now(UTC).replace(microsecond=0)
    run = SimpleNamespace(
        id=88,
        candidate_session_id=9,
        scenario_version_id=7,
        status="running",
        started_at=now,
        completed_at=None,
        error_code=None,
        metadata_json={"jobId": "job-1"},
        model_name="model",
        model_version="v1",
        prompt_version="p1",
        rubric_version="r1",
        basis_fingerprint="fingerprint",
    )
    db = _DummyDB()

    async def _get_run(_db, _run_id, for_update=True):
        assert for_update is True
        return run

    monkeypatch.setattr(evaluation_runs.evaluation_repo, "get_run_by_id", _get_run)

    failed = await evaluation_runs.fail_run(
        db,
        run_id=run.id,
        completed_at=now + timedelta(seconds=1),
        commit=False,
        metadata_json=None,
        error_message=None,
    )

    assert failed is run
    assert run.status == "failed"
    assert run.metadata_json == {"jobId": "job-1"}
    assert db.flushes == 1


@pytest.mark.asyncio
async def test_update_simulation_without_notice_or_day_changes_skips_change_logs(
    monkeypatch,
):
    simulation = SimpleNamespace(
        id=45,
        ai_notice_version="notice-v1",
        ai_notice_text="text",
        ai_eval_enabled_by_day={"1": True, "2": False},
    )
    tasks = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
    db = _DummyDB()

    async def _require_owned_with_tasks(_db, _simulation_id, _actor_user_id):
        return simulation, tasks

    calls = {"resolve": 0}

    def _resolve_fields(**kwargs):
        calls["resolve"] += 1
        if calls["resolve"] == 1:
            return ("notice-v1", "text", {"1": True, "2": False})
        return ("notice-v1", "text", {"1": True, "2": False})

    payload = SimpleNamespace(
        ai=SimpleNamespace(
            model_fields_set={"notice_version", "notice_text", "eval_enabled_by_day"},
            notice_version="notice-v1",
            notice_text="text",
            eval_enabled_by_day={"1": True, "2": False},
        )
    )

    monkeypatch.setattr(
        simulations_update,
        "require_owned_simulation_with_tasks",
        _require_owned_with_tasks,
    )
    monkeypatch.setattr(
        simulations_update, "resolve_simulation_ai_fields", _resolve_fields
    )

    updated_simulation, updated_tasks = await simulations_update.update_simulation(
        db,
        simulation_id=45,
        actor_user_id=99,
        payload=payload,
    )

    assert updated_simulation is simulation
    assert updated_tasks == tasks
    assert db.commits == 1
    assert db.refreshes == 3
