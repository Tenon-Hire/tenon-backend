"""Application module for integrations github webhooks signature utils workflows."""

from __future__ import annotations

import hashlib
import hmac

_SIGNATURE_PREFIX = "sha256="


def build_github_signature(secret: str, raw_body: bytes) -> str:
    """Return the GitHub SHA-256 signature value for a payload."""
    digest = hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return f"{_SIGNATURE_PREFIX}{digest}"


def verify_github_signature(
    secret: str,
    raw_body: bytes,
    provided_signature: str | None,
) -> bool:
    """Verify the X-Hub-Signature-256 header against the raw body."""
    normalized_secret = (secret or "").strip()
    normalized_header = (provided_signature or "").strip()
    if not normalized_secret or not normalized_header:
        return False
    if not normalized_header.startswith(_SIGNATURE_PREFIX):
        return False

    expected_signature = build_github_signature(normalized_secret, raw_body)
    return hmac.compare_digest(expected_signature, normalized_header)


__all__ = ["build_github_signature", "verify_github_signature"]
