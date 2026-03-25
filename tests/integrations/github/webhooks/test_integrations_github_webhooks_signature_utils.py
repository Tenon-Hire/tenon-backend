from app.integrations.github.webhooks.integrations_github_webhooks_signature_utils import (
    build_github_signature,
    verify_github_signature,
)


def test_verify_github_signature_accepts_valid_value():
    secret = "webhook-secret"
    raw_body = b'{"ok":true}'
    signature = build_github_signature(secret, raw_body)

    assert verify_github_signature(secret, raw_body, signature) is True


def test_verify_github_signature_rejects_missing_value():
    assert verify_github_signature("webhook-secret", b'{"ok":true}', None) is False


def test_verify_github_signature_rejects_invalid_value():
    secret = "webhook-secret"
    raw_body = b'{"ok":true}'

    assert (
        verify_github_signature(
            secret,
            raw_body,
            "sha256=0000000000000000000000000000000000000000000000000000000000000000",
        )
        is False
    )


def test_verify_github_signature_rejects_wrong_prefix():
    assert (
        verify_github_signature(
            "webhook-secret",
            b'{"ok":true}',
            "sha1=abc123",
        )
        is False
    )
