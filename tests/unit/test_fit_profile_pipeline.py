from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.repositories.evaluations.models import (
    EVALUATION_RUN_STATUS_COMPLETED,
    EVALUATION_RUN_STATUS_FAILED,
)
from app.services.evaluations import fit_profile_pipeline


class _ScalarOneResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeDB:
    def __init__(self, *, get_value=None, execute_values=None):
        self._get_value = get_value
        self._execute_values = list(execute_values or [])

    async def get(self, *_args, **_kwargs):
        return self._get_value

    async def execute(self, *_args, **_kwargs):
        value = self._execute_values.pop(0) if self._execute_values else None
        return _ScalarOneResult(value)


class _SessionContext:
    def __init__(self, db):
        self._db = db

    async def __aenter__(self):
        return self._db

    async def __aexit__(self, exc_type, exc, tb):
        del exc_type, exc, tb
        return False


def _session_maker_for(db):
    def _maker():
        return _SessionContext(db)

    return _maker


def test_fit_profile_pipeline_helper_parsing_and_hashes():
    assert fit_profile_pipeline._parse_positive_int(True) is None
    assert fit_profile_pipeline._parse_positive_int(-1) is None
    assert fit_profile_pipeline._parse_positive_int("7") == 7
    assert fit_profile_pipeline._safe_int(True) is None
    assert fit_profile_pipeline._safe_int(9) == 9
    assert fit_profile_pipeline._safe_int(9.8) == 9
    assert fit_profile_pipeline._segment_start_ms({"x": 1}) is None
    assert fit_profile_pipeline._segment_end_ms({"x": 1}) is None
    assert fit_profile_pipeline._parse_diff_summary(None) is None
    assert fit_profile_pipeline._parse_diff_summary("not-json") is None
    assert fit_profile_pipeline._parse_diff_summary("[1,2,3]") is None
    assert fit_profile_pipeline._parse_diff_summary('{"base":"a","head":"b"}') == {
        "base": "a",
        "head": "b",
    }
    assert fit_profile_pipeline._submission_basis_hash(None) is None
    assert fit_profile_pipeline._transcript_basis_hash(None) is None

    enabled, disabled = fit_profile_pipeline._normalize_day_toggles(
        {"2": False, "4": False}
    )
    assert enabled == [1, 3, 5]
    assert disabled == [2, 4]

    digest_one = fit_profile_pipeline._stable_hash({"x": 1, "y": [2, 3]})
    digest_two = fit_profile_pipeline._stable_hash({"y": [2, 3], "x": 1})
    assert digest_one == digest_two


def test_fit_profile_pipeline_normalize_transcript_segments():
    normalized = fit_profile_pipeline._normalize_transcript_segments(
        [
            "skip",
            {"startMs": 10, "endMs": 9, "text": "  message  "},
            {"start_ms": -20, "end_ms": 30, "content": "Alt keys"},
            {"start": 40.4, "end": 44.9, "excerpt": "From excerpt"},
            {"startMs": 100},  # missing end
            {"endMs": 200},  # missing start
        ]
    )

    assert normalized == [
        {"startMs": 10, "endMs": 10, "text": "  message  "},
        {"startMs": 0, "endMs": 30, "text": "Alt keys"},
        {"startMs": 40, "endMs": 44, "text": "From excerpt"},
    ]


@pytest.mark.asyncio
async def test_resolve_day4_transcript_missing_branches():
    no_recording = _FakeDB()
    transcript, ref = await fit_profile_pipeline._resolve_day4_transcript(
        no_recording,
        candidate_session_id=1,
        day4_task=None,
        day4_submission=None,
    )
    assert transcript is None
    assert ref == "transcript:missing"

    with_submission_recording = _FakeDB(
        get_value=SimpleNamespace(id=7),
        execute_values=[None],
    )
    transcript, ref = await fit_profile_pipeline._resolve_day4_transcript(
        with_submission_recording,
        candidate_session_id=1,
        day4_task=None,
        day4_submission=SimpleNamespace(recording_id=7),
    )
    assert transcript is None
    assert ref == "transcript:recording:7:missing"

    fallback_recording = _FakeDB(
        get_value=None,
        execute_values=[
            SimpleNamespace(id=8),
            SimpleNamespace(id=9, recording_id=8),
        ],
    )
    transcript, ref = await fit_profile_pipeline._resolve_day4_transcript(
        fallback_recording,
        candidate_session_id=1,
        day4_task=SimpleNamespace(id=444),
        day4_submission=SimpleNamespace(recording_id=None),
    )
    assert transcript is not None
    assert transcript.id == 9
    assert ref == "transcript:9"


@pytest.mark.asyncio
async def test_process_evaluation_run_job_invalid_payload():
    response = await fit_profile_pipeline.process_evaluation_run_job(
        {"candidateSessionId": True, "companyId": 2}
    )
    assert response == {
        "status": "skipped_invalid_payload",
        "candidateSessionId": None,
        "companyId": 2,
    }


@pytest.mark.asyncio
async def test_process_evaluation_run_job_candidate_session_not_found(monkeypatch):
    db = SimpleNamespace()
    monkeypatch.setattr(
        fit_profile_pipeline,
        "async_session_maker",
        _session_maker_for(db),
    )
    monkeypatch.setattr(
        fit_profile_pipeline,
        "get_candidate_session_evaluation_context",
        AsyncMock(return_value=None),
    )

    response = await fit_profile_pipeline.process_evaluation_run_job(
        {"candidateSessionId": 10, "companyId": 20}
    )
    assert response == {
        "status": "candidate_session_not_found",
        "candidateSessionId": 10,
    }


@pytest.mark.asyncio
async def test_process_evaluation_run_job_company_forbidden(monkeypatch):
    db = SimpleNamespace()
    context = SimpleNamespace(
        candidate_session=SimpleNamespace(id=10, scenario_version_id=12),
        simulation=SimpleNamespace(id=14, company_id=200, ai_eval_enabled_by_day={}),
        scenario_version=None,
    )
    monkeypatch.setattr(
        fit_profile_pipeline,
        "async_session_maker",
        _session_maker_for(db),
    )
    monkeypatch.setattr(
        fit_profile_pipeline,
        "get_candidate_session_evaluation_context",
        AsyncMock(return_value=context),
    )
    monkeypatch.setattr(
        fit_profile_pipeline, "has_company_access", lambda **_kwargs: False
    )

    response = await fit_profile_pipeline.process_evaluation_run_job(
        {"candidateSessionId": 10, "companyId": 201}
    )
    assert response == {"status": "company_access_forbidden", "candidateSessionId": 10}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("run_status", "error_code", "expected_status"),
    [
        (EVALUATION_RUN_STATUS_COMPLETED, None, "completed"),
        (EVALUATION_RUN_STATUS_FAILED, "evaluation_failed", "failed"),
    ],
)
async def test_process_evaluation_run_job_reuses_existing_terminal_run(
    monkeypatch,
    run_status,
    error_code,
    expected_status,
):
    db = SimpleNamespace()
    context = SimpleNamespace(
        candidate_session=SimpleNamespace(id=50, scenario_version_id=60),
        simulation=SimpleNamespace(id=70, company_id=80, ai_eval_enabled_by_day={}),
        scenario_version=SimpleNamespace(rubric_version="rubric-vx"),
    )
    existing_run = SimpleNamespace(
        id=99,
        status=run_status,
        model_version="2026-03-12",
        prompt_version="fit-profile-v1",
        rubric_version="rubric-vx",
        basis_fingerprint="abc123",
        error_code=error_code,
    )

    start_run = AsyncMock(side_effect=AssertionError("start_run should not be called"))
    monkeypatch.setattr(
        fit_profile_pipeline,
        "async_session_maker",
        _session_maker_for(db),
    )
    monkeypatch.setattr(
        fit_profile_pipeline,
        "get_candidate_session_evaluation_context",
        AsyncMock(return_value=context),
    )
    monkeypatch.setattr(
        fit_profile_pipeline, "has_company_access", lambda **_kwargs: True
    )
    monkeypatch.setattr(
        fit_profile_pipeline, "_tasks_by_day", AsyncMock(return_value={})
    )
    monkeypatch.setattr(
        fit_profile_pipeline,
        "_submissions_by_day",
        AsyncMock(return_value={}),
    )
    monkeypatch.setattr(
        fit_profile_pipeline,
        "_day_audits_by_day",
        AsyncMock(return_value={}),
    )
    monkeypatch.setattr(
        fit_profile_pipeline,
        "_resolve_day4_transcript",
        AsyncMock(return_value=(None, "transcript:missing")),
    )
    monkeypatch.setattr(
        fit_profile_pipeline.evaluation_repo,
        "get_run_by_job_id",
        AsyncMock(return_value=existing_run),
    )
    monkeypatch.setattr(fit_profile_pipeline.evaluation_runs, "start_run", start_run)

    response = await fit_profile_pipeline.process_evaluation_run_job(
        {
            "candidateSessionId": 50,
            "companyId": 80,
            "requestedByUserId": 77,
            "jobId": "job-abc",
        }
    )
    assert response["status"] == expected_status
    assert response["candidateSessionId"] == 50
    assert response["evaluationRunId"] == 99
    start_run.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_evaluation_run_job_skips_job_lookup_when_job_id_missing(
    monkeypatch,
):
    db = SimpleNamespace(commit=AsyncMock())
    context = SimpleNamespace(
        candidate_session=SimpleNamespace(id=50, scenario_version_id=60),
        simulation=SimpleNamespace(id=70, company_id=80, ai_eval_enabled_by_day={}),
        scenario_version=SimpleNamespace(rubric_version="rubric-vx"),
    )
    evaluator = SimpleNamespace(
        evaluate=AsyncMock(
            return_value=SimpleNamespace(
                day_results=[],
                overall_fit_score=87,
                recommendation="strong_hire",
                confidence=0.91,
                report_json={"summary": "ok"},
            )
        )
    )
    get_run_by_job_id = AsyncMock(return_value=None)
    start_run = AsyncMock(
        return_value=SimpleNamespace(
            id=123,
            status="running",
        )
    )
    complete_run = AsyncMock(
        return_value=SimpleNamespace(
            id=123,
            generated_at=datetime(2026, 3, 19, 0, 0, tzinfo=UTC),
            model_version="2026-03-12",
            prompt_version="fit-profile-v1",
            rubric_version="rubric-vx",
            basis_fingerprint="basis-123",
        )
    )

    monkeypatch.setattr(
        fit_profile_pipeline,
        "async_session_maker",
        _session_maker_for(db),
    )
    monkeypatch.setattr(
        fit_profile_pipeline,
        "get_candidate_session_evaluation_context",
        AsyncMock(return_value=context),
    )
    monkeypatch.setattr(
        fit_profile_pipeline, "has_company_access", lambda **_kwargs: True
    )
    monkeypatch.setattr(
        fit_profile_pipeline, "_tasks_by_day", AsyncMock(return_value={})
    )
    monkeypatch.setattr(
        fit_profile_pipeline,
        "_submissions_by_day",
        AsyncMock(return_value={}),
    )
    monkeypatch.setattr(
        fit_profile_pipeline,
        "_day_audits_by_day",
        AsyncMock(return_value={}),
    )
    monkeypatch.setattr(
        fit_profile_pipeline,
        "_resolve_day4_transcript",
        AsyncMock(return_value=(None, "transcript:missing")),
    )
    monkeypatch.setattr(
        fit_profile_pipeline.evaluation_repo,
        "get_run_by_job_id",
        get_run_by_job_id,
    )
    monkeypatch.setattr(fit_profile_pipeline.evaluation_runs, "start_run", start_run)
    monkeypatch.setattr(
        fit_profile_pipeline.evaluation_runs,
        "complete_run",
        complete_run,
    )
    monkeypatch.setattr(
        fit_profile_pipeline.fit_profile_repository,
        "upsert_marker",
        AsyncMock(),
    )
    monkeypatch.setattr(
        fit_profile_pipeline.evaluator_service,
        "get_fit_profile_evaluator",
        lambda: evaluator,
    )

    response = await fit_profile_pipeline.process_evaluation_run_job(
        {
            "candidateSessionId": 50,
            "companyId": 80,
            "requestedByUserId": 77,
        }
    )
    assert response["status"] == "completed"
    assert response["evaluationRunId"] == 123
    get_run_by_job_id.assert_not_awaited()
    start_run.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_evaluation_run_job_continues_when_existing_run_not_terminal(
    monkeypatch,
):
    db = SimpleNamespace(commit=AsyncMock())
    context = SimpleNamespace(
        candidate_session=SimpleNamespace(id=50, scenario_version_id=60),
        simulation=SimpleNamespace(id=70, company_id=80, ai_eval_enabled_by_day={}),
        scenario_version=SimpleNamespace(rubric_version="rubric-vx"),
    )
    existing_run = SimpleNamespace(id=99, status="running")
    evaluator = SimpleNamespace(
        evaluate=AsyncMock(
            return_value=SimpleNamespace(
                day_results=[],
                overall_fit_score=82,
                recommendation="hire",
                confidence=0.77,
                report_json={"summary": "in_progress_then_completed"},
            )
        )
    )
    start_run = AsyncMock(side_effect=AssertionError("start_run should not be called"))
    complete_run = AsyncMock(
        return_value=SimpleNamespace(
            id=99,
            generated_at=datetime(2026, 3, 19, 0, 5, tzinfo=UTC),
            model_version="2026-03-12",
            prompt_version="fit-profile-v1",
            rubric_version="rubric-vx",
            basis_fingerprint="basis-99",
        )
    )

    monkeypatch.setattr(
        fit_profile_pipeline,
        "async_session_maker",
        _session_maker_for(db),
    )
    monkeypatch.setattr(
        fit_profile_pipeline,
        "get_candidate_session_evaluation_context",
        AsyncMock(return_value=context),
    )
    monkeypatch.setattr(
        fit_profile_pipeline, "has_company_access", lambda **_kwargs: True
    )
    monkeypatch.setattr(
        fit_profile_pipeline, "_tasks_by_day", AsyncMock(return_value={})
    )
    monkeypatch.setattr(
        fit_profile_pipeline,
        "_submissions_by_day",
        AsyncMock(return_value={}),
    )
    monkeypatch.setattr(
        fit_profile_pipeline,
        "_day_audits_by_day",
        AsyncMock(return_value={}),
    )
    monkeypatch.setattr(
        fit_profile_pipeline,
        "_resolve_day4_transcript",
        AsyncMock(return_value=(None, "transcript:missing")),
    )
    monkeypatch.setattr(
        fit_profile_pipeline.evaluation_repo,
        "get_run_by_job_id",
        AsyncMock(return_value=existing_run),
    )
    monkeypatch.setattr(fit_profile_pipeline.evaluation_runs, "start_run", start_run)
    monkeypatch.setattr(
        fit_profile_pipeline.evaluation_runs,
        "complete_run",
        complete_run,
    )
    monkeypatch.setattr(
        fit_profile_pipeline.fit_profile_repository,
        "upsert_marker",
        AsyncMock(),
    )
    monkeypatch.setattr(
        fit_profile_pipeline.evaluator_service,
        "get_fit_profile_evaluator",
        lambda: evaluator,
    )

    response = await fit_profile_pipeline.process_evaluation_run_job(
        {
            "candidateSessionId": 50,
            "companyId": 80,
            "requestedByUserId": 77,
            "jobId": "job-abc",
        }
    )
    assert response["status"] == "completed"
    assert response["evaluationRunId"] == 99
    start_run.assert_not_awaited()


def test_build_basis_references_captures_hashes():
    submission = SimpleNamespace(
        id=7,
        submitted_at=datetime(2026, 3, 12, 14, 0, tzinfo=UTC),
        content_text="text",
        content_json={"k": "v"},
        commit_sha="abc",
        checkpoint_sha="def",
        final_sha="ghi",
        workflow_run_id="123",
        diff_summary_json='{"base":"x","head":"y"}',
        tests_passed=4,
        tests_failed=1,
        test_output="ok",
        last_run_at=datetime(2026, 3, 12, 14, 5, tzinfo=UTC),
    )
    day_audit = SimpleNamespace(cutoff_commit_sha="cutoff", eval_basis_ref="basis-ref")

    references = fit_profile_pipeline._build_basis_references(
        scenario_version_id=22,
        scenario_rubric_version="rubric-v2",
        day_audits={2: day_audit},
        submissions_by_day={2: submission},
        transcript_reference="transcript:11",
        transcript_hash="hash-11",
        disabled_day_indexes=[4],
    )

    assert references["scenarioVersionId"] == 22
    assert references["rubricVersion"] == "rubric-v2"
    assert references["dayRefs"]["2"]["submissionId"] == 7
    assert references["dayRefs"]["2"]["cutoffCommitSha"] == "cutoff"
    assert references["transcriptReference"] == "transcript:11"
    assert references["disabledDayIndexes"] == [4]
