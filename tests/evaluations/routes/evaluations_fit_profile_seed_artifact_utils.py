from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.candidate_sessions.repositories import repository as cs_repo
from app.media.repositories.recordings import repository as recordings_repo
from app.media.repositories.recordings.media_repositories_recordings_media_recordings_core_model import (
    RECORDING_ASSET_STATUS_READY,
)
from app.media.repositories.transcripts import repository as transcripts_repo
from app.media.repositories.transcripts.media_repositories_transcripts_media_transcripts_core_model import (
    TRANSCRIPT_STATUS_READY,
)
from tests.shared.factories import create_submission


async def _seed_handoff_and_reflection(
    async_session: AsyncSession,
    *,
    candidate_session,
    tasks_by_day,
) -> None:
    recording = await recordings_repo.create_recording_asset(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=tasks_by_day[4].id,
        storage_key=f"candidate-sessions/{candidate_session.id}/task4/video.webm",
        content_type="video/webm",
        bytes_count=1024,
        status=RECORDING_ASSET_STATUS_READY,
        commit=False,
    )
    await create_submission(
        async_session,
        candidate_session=candidate_session,
        task=tasks_by_day[4],
        content_text="handoff summary",
        recording_id=recording.id,
    )
    await transcripts_repo.create_transcript(
        async_session,
        recording_id=recording.id,
        status=TRANSCRIPT_STATUS_READY,
        text="I refactored the service layer and added tests.",
        segments_json=[
            {"startMs": 100, "endMs": 1200, "text": "I refactored the service layer."},
            {"startMs": 1300, "endMs": 2600, "text": "I added regression tests."},
        ],
        model_name="whisper-test",
        commit=False,
    )
    await create_submission(
        async_session,
        candidate_session=candidate_session,
        task=tasks_by_day[5],
        content_text="Reflection on constraints and communication.",
        content_json={"kind": "day5_reflection", "sections": {"reflection": "done"}},
    )


async def _seed_cutoff_day_audits(
    async_session: AsyncSession, *, candidate_session_id: int
) -> None:
    cutoff_at = datetime.now(UTC).replace(microsecond=0)
    await cs_repo.create_day_audit_once(
        async_session,
        candidate_session_id=candidate_session_id,
        day_index=2,
        cutoff_at=cutoff_at,
        cutoff_commit_sha="cutoff-day2-fixed",
        eval_basis_ref="refs/heads/main@cutoff:day2",
        commit=False,
    )
    await cs_repo.create_day_audit_once(
        async_session,
        candidate_session_id=candidate_session_id,
        day_index=3,
        cutoff_at=cutoff_at,
        cutoff_commit_sha="cutoff-day3-fixed",
        eval_basis_ref="refs/heads/main@cutoff:day3",
        commit=False,
    )
