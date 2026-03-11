import pytest
from sqlalchemy import inspect


@pytest.mark.asyncio
async def test_media_tables_have_expected_columns(db_engine):
    async with db_engine.begin() as conn:
        recording_columns = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_columns("recording_assets")
        )
        transcript_columns = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_columns("transcripts")
        )
        submission_columns = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_columns("submissions")
        )

    recording_names = {col["name"] for col in recording_columns}
    transcript_names = {col["name"] for col in transcript_columns}
    submission_names = {col["name"] for col in submission_columns}

    assert {
        "id",
        "candidate_session_id",
        "task_id",
        "storage_key",
        "content_type",
        "bytes",
        "status",
        "created_at",
    }.issubset(recording_names)

    assert {
        "id",
        "recording_id",
        "text",
        "segments_json",
        "model_name",
        "last_error",
        "status",
        "created_at",
    }.issubset(transcript_names)

    assert {"recording_id"}.issubset(submission_names)
