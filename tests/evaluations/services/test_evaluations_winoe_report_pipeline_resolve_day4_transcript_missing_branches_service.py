from __future__ import annotations

import pytest

from tests.evaluations.services.evaluations_winoe_report_pipeline_utils import *


@pytest.mark.asyncio
async def test_resolve_day4_transcript_missing_branches():
    no_recording = _FakeDB()
    transcript, ref = await winoe_report_pipeline._resolve_day4_transcript(
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
    transcript, ref = await winoe_report_pipeline._resolve_day4_transcript(
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
    transcript, ref = await winoe_report_pipeline._resolve_day4_transcript(
        fallback_recording,
        candidate_session_id=1,
        day4_task=SimpleNamespace(id=444),
        day4_submission=SimpleNamespace(recording_id=None),
    )
    assert transcript is not None
    assert transcript.id == 9
    assert ref == "transcript:9"
