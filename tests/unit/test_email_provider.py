from app.infra.notifications.email_provider import _parse_sender


def test_parse_sender_with_name():
    email, name = _parse_sender("Tenon <noreply@test.com>")
    assert email == "noreply@test.com"
    assert name == "Tenon"


def test_parse_sender_without_name():
    email, name = _parse_sender("noreply@test.com")
    assert email == "noreply@test.com"
    assert name is None
