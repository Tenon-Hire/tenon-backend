"""Application module for integrations email provider memory client workflows."""

from __future__ import annotations

from .integrations_email_email_provider_base_client import EmailMessage


class MemoryEmailProvider:
    """Test helper that captures sent messages in memory."""

    def __init__(self):
        self.sent: list[EmailMessage] = []

    async def send(self, message: EmailMessage) -> str | None:
        """Send the requested communication."""
        self.sent.append(message)
        return f"memory-{len(self.sent)}"
