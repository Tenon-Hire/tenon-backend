from __future__ import annotations

from .integrations_email_email_provider_base_client import EmailMessage
from .integrations_email_email_provider_smtp_transport_client import send_smtp


class SMTPEmailProvider:
    def __init__(
        self,
        host: str,
        port: int = 587,
        *,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool = True,
        sender: str | None = None,
    ):
        if not host:
            raise ValueError("SMTP_HOST is required for SMTP provider")
        self.host = host
        self.port = port
        self.username = username or ""
        self.password = password or ""
        self.use_tls = use_tls
        self.sender = sender

    async def send(self, message: EmailMessage) -> str | None:
        return await send_smtp(
            message,
            host=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            use_tls=self.use_tls,
            sender=self.sender,
        )
