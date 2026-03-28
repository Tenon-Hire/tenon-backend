"""Application module for notifications services notifications email sender service workflows."""

from __future__ import annotations

import asyncio
import time

from app.integrations.email.email_provider import (
    EmailMessage,
    EmailProvider,
    EmailSendError,
)
from app.notifications.schemas.notifications_schemas_notifications_email_schema import (
    EmailSendResult,
    EmailStatus,
)
from app.shared.utils import shared_utils_perf_utils as perf


class EmailSender:
    """High-level email sender with minimal retry support."""

    def __init__(self, provider: EmailProvider, *, sender: str, max_attempts: int = 2):
        self.provider = provider
        self.sender = sender
        self.max_attempts = max(1, max_attempts)

    async def send_email(
        self, *, to: str, subject: str, text: str, html: str | None = None
    ) -> EmailSendResult:
        """Send email."""
        last_error: EmailSendError | None = None
        for attempt in range(self.max_attempts):
            try:
                started = time.perf_counter()
                try:
                    message_id = await self.provider.send(
                        EmailMessage(
                            to=to,
                            subject=subject,
                            text=text,
                            html=html,
                            sender=self.sender,
                        )
                    )
                finally:
                    perf.record_external_wait(
                        "email", (time.perf_counter() - started) * 1000.0
                    )
                return EmailSendResult(status="sent", message_id=message_id)
            except EmailSendError as exc:
                last_error = exc
                should_retry = exc.retryable and attempt < self.max_attempts - 1
                if not should_retry:
                    break
                await asyncio.sleep(0.05 * (attempt + 1))
        return EmailSendResult(
            status="failed",
            message_id=None,
            error=str(last_error) if last_error else "Email send failed",
        )


# Backwards-compat alias
EmailService = EmailSender
__all__ = ["EmailSender", "EmailService", "EmailSendResult", "EmailStatus"]
