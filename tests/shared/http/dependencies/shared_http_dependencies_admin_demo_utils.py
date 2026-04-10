from __future__ import annotations

from fastapi import Request

import app.shared.http.dependencies.shared_http_dependencies_admin_demo_utils as admin_demo
from app.config import settings
from app.shared.auth.principal import Principal


def principal(
    *, email: str, sub: str, roles: list[str] | None = None, claims: dict | None = None
) -> Principal:
    payload = {"sub": sub, "email": email}
    if claims:
        payload.update(claims)
    return Principal(
        sub=sub,
        email=email,
        name="admin",
        roles=roles or [],
        permissions=["talent_partner:access"],
        claims=payload,
    )


def request() -> Request:
    scope = {
        "type": "http",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "path": "/api/admin/jobs/job/requeue",
        "method": "POST",
        "query_string": b"",
        "server": ("testserver", 80),
    }

    async def _receive():
        return {"type": "http.request"}

    return Request(scope, _receive)


def patch_get_principal(monkeypatch, actor: Principal) -> None:
    async def _fake_get_principal(_credentials, _request):
        return actor

    monkeypatch.setattr(admin_demo, "get_principal", _fake_get_principal)


def patch_demo_settings(
    monkeypatch,
    *,
    demo_mode: bool = True,
    emails=None,
    subjects=None,
    talent_partner_ids=None,
):
    monkeypatch.setattr(settings, "DEMO_MODE", demo_mode)
    monkeypatch.setattr(settings, "DEMO_ADMIN_ALLOWLIST_EMAILS", emails or [])
    monkeypatch.setattr(settings, "DEMO_ADMIN_ALLOWLIST_SUBJECTS", subjects or [])
    monkeypatch.setattr(
        settings, "DEMO_ADMIN_ALLOWLIST_TALENT_PARTNER_IDS", talent_partner_ids or []
    )
