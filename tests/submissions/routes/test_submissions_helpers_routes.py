import pytest
from fastapi import HTTPException

from app.shared.http.routes import submissions
from tests.shared.factories import create_talent_partner


def test_derive_test_status_variants():
    assert submissions._derive_test_status(None, None, None) is None
    assert submissions._derive_test_status(None, 1, "oops") == "failed"
    assert submissions._derive_test_status(2, 0, "ok") == "passed"
    assert submissions._derive_test_status(None, None, "  logs  ") == "unknown"


@pytest.mark.asyncio
async def test_get_submission_detail_not_found(async_session):
    user = await create_talent_partner(async_session, email="missing-sub@sim.com")
    with pytest.raises(HTTPException) as exc:
        await submissions.get_submission_detail(
            submission_id=9999, db=async_session, user=user
        )
    assert exc.value.status_code == 404


def test_submissions_helper_redaction_and_truncate():
    assert submissions._redact_text(None) is None
    redacted = submissions._redact_text("Authorization: Bearer secret-token")
    assert "redacted" in redacted
    text, truncated = submissions._truncate_output("short", max_chars=10)
    assert text == "short" and truncated is False
    text, truncated = submissions._truncate_output("longertext", max_chars=3)
    assert text.endswith("... (truncated)") and truncated is True
    assert submissions._parse_diff_summary("{bad") is None


def test_submissions_helpers_empty_inputs_cover_branches():
    assert submissions._truncate_output(None, max_chars=5) == (None, None)
    assert submissions._build_diff_url("repo/name", {"base": None}) is None
