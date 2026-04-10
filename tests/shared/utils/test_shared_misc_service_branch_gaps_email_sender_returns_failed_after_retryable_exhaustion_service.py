from __future__ import annotations

import pytest

from tests.shared.utils.shared_misc_service_branch_gaps_utils import *


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
    sender = EmailSender(_Provider(), sender="noreply@winoe.ai", max_attempts=2)

    result = await sender.send_email(
        to="candidate@example.com",
        subject="subject",
        text="body",
    )

    assert result.status == "failed"
    assert calls["count"] == 2
