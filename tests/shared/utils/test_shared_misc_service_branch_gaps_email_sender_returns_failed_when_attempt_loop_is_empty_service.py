from __future__ import annotations

import pytest

from tests.shared.utils.shared_misc_service_branch_gaps_utils import *


@pytest.mark.asyncio
async def test_email_sender_returns_failed_when_attempt_loop_is_empty():
    class _Provider:
        async def send(self, _message):
            raise AssertionError("provider.send should not be called")

    sender = EmailSender(_Provider(), sender="noreply@winoe.ai", max_attempts=1)
    sender.max_attempts = 0

    result = await sender.send_email(
        to="candidate@example.com",
        subject="subject",
        text="body",
    )

    assert result.status == "failed"
    assert result.error == "Email send failed"
