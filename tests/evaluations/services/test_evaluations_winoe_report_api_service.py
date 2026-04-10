from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.evaluations.services import winoe_report_api
from tests.evaluations.services.evaluations_winoe_report_api_utils import build_context


@pytest.mark.asyncio
async def test_require_talent_partner_candidate_session_context_404(monkeypatch):
    async def _missing_context(_db, *, candidate_session_id):
        assert candidate_session_id == 999
        return None

    monkeypatch.setattr(
        winoe_report_api, "get_candidate_session_evaluation_context", _missing_context
    )
    with pytest.raises(HTTPException) as exc:
        await winoe_report_api.require_talent_partner_candidate_session_context(
            object(),
            candidate_session_id=999,
            user=SimpleNamespace(company_id=1),
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_require_talent_partner_candidate_session_context_403(monkeypatch):
    async def _context(_db, *, candidate_session_id):
        assert candidate_session_id == 12
        return build_context(candidate_session_id=12, company_id=5)

    monkeypatch.setattr(
        winoe_report_api, "get_candidate_session_evaluation_context", _context
    )
    monkeypatch.setattr(winoe_report_api, "has_company_access", lambda **_kwargs: False)
    with pytest.raises(HTTPException) as exc:
        await winoe_report_api.require_talent_partner_candidate_session_context(
            object(),
            candidate_session_id=12,
            user=SimpleNamespace(company_id=999),
        )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_require_talent_partner_candidate_session_context_success(monkeypatch):
    context = build_context(candidate_session_id=15, company_id=3)
    monkeypatch.setattr(
        winoe_report_api,
        "get_candidate_session_evaluation_context",
        AsyncMock(return_value=context),
    )
    monkeypatch.setattr(winoe_report_api, "has_company_access", lambda **_kwargs: True)
    resolved = await winoe_report_api.require_talent_partner_candidate_session_context(
        object(),
        candidate_session_id=15,
        user=SimpleNamespace(company_id=3),
    )
    assert resolved is context
