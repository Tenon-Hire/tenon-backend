import pytest

from app.integrations.email.email_provider import EmailMessage, SMTPEmailProvider
from app.integrations.email.email_provider import (
    integrations_email_email_provider_smtp_transport_client as smtp_transport,
)


@pytest.mark.asyncio
async def test_smtp_provider_send(monkeypatch):
    calls = {"starttls": 0, "login": 0, "send": 0}

    class FakeSMTP:
        def __init__(self, host, port, timeout=10):
            self.host = host
            self.port = port
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def ehlo(self):
            return None

        def starttls(self, context=None):
            calls["starttls"] += 1
            assert context is not None

        def login(self, username, password):
            calls["login"] += 1
            assert username == "user"
            assert password == "pass"

        def send_message(self, message):
            calls["send"] += 1
            assert message["To"] == "to@test.com"

    monkeypatch.setattr("smtplib.SMTP", FakeSMTP)
    provider = SMTPEmailProvider(
        host="smtp.test",
        username="user",
        password="pass",
        use_tls=True,
        sender="sender@test.com",
    )
    await provider.send(
        EmailMessage(to="to@test.com", subject="Hi", text="Body", html="<b>Body</b>")
    )
    assert calls["starttls"] == 1
    assert calls["login"] == 1
    assert calls["send"] == 1


def test_smtp_transport_build_std_email_without_html():
    std_email = smtp_transport._build_std_email(
        EmailMessage(to="to@test.com", subject="Hi", text="Body"),
        sender="sender@test.com",
    )

    assert std_email["From"] == "sender@test.com"
    assert std_email.get_content_type() == "text/plain"
    assert std_email.is_multipart() is False


def test_smtp_transport_send_sync_skips_tls_and_login(monkeypatch):
    calls = {"starttls": 0, "login": 0, "send": 0}

    class FakeSMTP:
        def __init__(self, host, port, timeout=10):
            self.host = host
            self.port = port
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def ehlo(self):
            return None

        def starttls(self, context=None):
            calls["starttls"] += 1

        def login(self, username, password):
            calls["login"] += 1

        def send_message(self, message):
            calls["send"] += 1
            assert message["To"] == "to@test.com"

    monkeypatch.setattr(smtp_transport.smtplib, "SMTP", FakeSMTP)
    std_email = smtp_transport._build_std_email(
        EmailMessage(to="to@test.com", subject="Hi", text="Body"),
        sender="sender@test.com",
    )
    smtp_transport._send_sync(
        std_email,
        host="smtp.test",
        port=25,
        username="",
        password="",
        use_tls=False,
    )

    assert calls["starttls"] == 0
    assert calls["login"] == 0
    assert calls["send"] == 1
