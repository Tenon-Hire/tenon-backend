from __future__ import annotations

import pytest

from tests.shared.utils.shared_perf_pass2_branch_coverage_utils import *


@pytest.mark.asyncio
async def test_invite_content_handles_naive_expiration_datetime():
    trial = SimpleNamespace(title="Backend Pass", role="Engineer")
    subject, text, html = invite_content.invite_email_content(
        candidate_name="Casey",
        invite_url="https://example.com/invite/123",
        trial=trial,
        expires_at=datetime(2026, 3, 21, 12, 0, 0),  # intentionally naive
    )
    assert "Backend Pass" in subject
    assert "2026-03-21" in text
    assert "2026-03-21" in html
