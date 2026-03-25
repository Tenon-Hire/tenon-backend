import json

import httpx
import pytest

from app.integrations.email.email_provider import (
    EmailMessage,
    EmailSendError,
    ResendEmailProvider,
)


@pytest.mark.asyncio
async def test_resend_provider_success_with_html():
    def _handler(request):
        payload = json.loads(request.content)
        assert payload["from"] == "Sender <sender@test.com>"
        assert payload["to"] == ["to@test.com"]
        assert payload["subject"] == "Hello"
        assert payload["html"] == "<b>Hi</b>"
        assert request.headers["Authorization"].startswith("Bearer ")
        return httpx.Response(200, json={"id": "msg-123"})

    provider = ResendEmailProvider(
        api_key="key",
        sender="Sender <sender@test.com>",
        transport=httpx.MockTransport(_handler),
    )
    message_id = await provider.send(
        EmailMessage(to="to@test.com", subject="Hello", text="Hi", html="<b>Hi</b>")
    )
    assert message_id == "msg-123"


@pytest.mark.asyncio
async def test_resend_provider_status_error():
    provider = ResendEmailProvider(
        api_key="key",
        sender="sender@test.com",
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(500, json={"error": "boom"})
        ),
    )
    with pytest.raises(EmailSendError) as excinfo:
        await provider.send(EmailMessage(to="to@test.com", subject="Hi", text="Body"))
    assert excinfo.value.retryable is True


@pytest.mark.asyncio
async def test_resend_provider_handles_bad_json():
    provider = ResendEmailProvider(
        api_key="key",
        sender="sender@test.com",
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(200, content=b"not-json")
        ),
    )
    message_id = await provider.send(
        EmailMessage(to="to@test.com", subject="Hi", text="Body")
    )
    assert message_id is None
