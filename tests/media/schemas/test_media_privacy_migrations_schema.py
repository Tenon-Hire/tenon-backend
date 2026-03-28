from __future__ import annotations

from pathlib import Path

from tests.media.schemas.media_privacy_migrations_utils import (
    PRE_PRIVACY_REVISION,
    PRIVACY_REVISION,
    build_pre_revision_schema,
    columns_for,
    run_alembic,
)


def test_media_privacy_migration_upgrade_and_downgrade_smoke(tmp_path):
    sqlite_path = tmp_path / "media_privacy_migration_smoke.db"
    sqlite_url = f"sqlite:///{sqlite_path}"
    build_pre_revision_schema(sqlite_url)
    repo_root = Path(__file__).resolve().parents[3]

    run_alembic(repo_root, sqlite_url=sqlite_url, args=["upgrade", PRIVACY_REVISION])
    candidate_session_columns = columns_for(sqlite_url, "candidate_sessions")
    recording_columns = columns_for(sqlite_url, "recording_assets")
    transcript_columns = columns_for(sqlite_url, "transcripts")
    assert {"consent_version", "consent_timestamp", "ai_notice_version"}.issubset(
        candidate_session_columns
    )
    assert {
        "deleted_at",
        "purged_at",
        "consent_version",
        "consent_timestamp",
        "ai_notice_version",
    }.issubset(recording_columns)
    assert {"deleted_at"}.issubset(transcript_columns)

    run_alembic(
        repo_root, sqlite_url=sqlite_url, args=["downgrade", PRE_PRIVACY_REVISION]
    )
    downgraded_candidate_session_columns = columns_for(sqlite_url, "candidate_sessions")
    downgraded_recording_columns = columns_for(sqlite_url, "recording_assets")
    downgraded_transcript_columns = columns_for(sqlite_url, "transcripts")
    assert "consent_version" not in downgraded_candidate_session_columns
    assert "deleted_at" not in downgraded_recording_columns
    assert "purged_at" not in downgraded_recording_columns
    assert "deleted_at" not in downgraded_transcript_columns
