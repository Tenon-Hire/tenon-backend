import json

import httpx
import pytest

from app.integrations.email.email_provider import (
    EmailMessage,
    EmailSendError,
    SendGridEmailProvider,
)


@pytest.mark.asyncio
async def test_sendgrid_provider_success_with_name():
    def _handler(request):
        payload = json.loads(request.content)
        assert payload["from"]["email"] == "sender@test.com"
        assert payload["from"]["name"] == "Sender"
        return httpx.Response(202, headers={"X-Message-Id": "sg-1"})

    provider = SendGridEmailProvider(
        api_key="key",
        sender="Sender <sender@test.com>",
        transport=httpx.MockTransport(_handler),
    )
    message_id = await provider.send(
        EmailMessage(to="to@test.com", subject="Hi", text="Body")
    )
    assert message_id == "sg-1"


@pytest.mark.asyncio
async def test_sendgrid_provider_includes_html():
    def _handler(request):
        payload = json.loads(request.content)
        assert len(payload["content"]) == 2
        assert payload["content"][1]["type"] == "text/html"
        return httpx.Response(202, headers={"X-Message-Id": "sg-2"})

    provider = SendGridEmailProvider(
        api_key="key",
        sender="sender@test.com",
        transport=httpx.MockTransport(_handler),
    )
    message_id = await provider.send(
        EmailMessage(to="to@test.com", subject="Hi", text="Body", html="<b>Hi</b>")
    )
    assert message_id == "sg-2"


@pytest.mark.asyncio
async def test_sendgrid_provider_status_error():
    provider = SendGridEmailProvider(
        api_key="key",
        sender="sender@test.com",
        transport=httpx.MockTransport(lambda _request: httpx.Response(400)),
    )
    with pytest.raises(EmailSendError) as excinfo:
        await provider.send(EmailMessage(to="to@test.com", subject="Hi", text="Body"))
    assert excinfo.value.retryable is False
