from __future__ import annotations

# NOTE: Providers are split by transport; imports stay stable for callers.
from .integrations_email_email_provider_base_client import (
    EmailMessage,
    EmailProvider,
    EmailSendError,
)
from .integrations_email_email_provider_console_client import ConsoleEmailProvider
from .integrations_email_email_provider_helpers_client import parse_sender
from .integrations_email_email_provider_memory_client import MemoryEmailProvider
from .integrations_email_email_provider_resend_client import ResendEmailProvider
from .integrations_email_email_provider_sendgrid_client import SendGridEmailProvider
from .integrations_email_email_provider_smtp_client import SMTPEmailProvider

__all__ = [
    "ConsoleEmailProvider",
    "EmailMessage",
    "EmailProvider",
    "EmailSendError",
    "MemoryEmailProvider",
    "ResendEmailProvider",
    "SendGridEmailProvider",
    "SMTPEmailProvider",
    "parse_sender",
    "_parse_sender",
]

_parse_sender = parse_sender
