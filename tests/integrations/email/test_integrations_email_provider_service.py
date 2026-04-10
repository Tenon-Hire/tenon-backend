import pytest

from app.integrations.email.email_provider import (
    ResendEmailProvider,
    SendGridEmailProvider,
    SMTPEmailProvider,
    _parse_sender,
)


def test_parse_sender_with_name():
    email, name = _parse_sender("Winoe <noreply@test.com>")
    assert email == "noreply@test.com"
    assert name == "Winoe"


def test_parse_sender_without_name():
    email, name = _parse_sender("noreply@test.com")
    assert email == "noreply@test.com"
    assert name is None


def test_parse_sender_empty():
    email, name = _parse_sender("")
    assert email == ""
    assert name is None


def test_provider_validation_errors():
    with pytest.raises(ValueError):
        ResendEmailProvider("", sender="s")
    with pytest.raises(ValueError):
        SendGridEmailProvider("", sender="s")
    with pytest.raises(ValueError):
        SMTPEmailProvider("", sender="s")
