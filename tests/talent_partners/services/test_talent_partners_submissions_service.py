from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.submissions.services import service_talent_partner as svc


class _DummyResult:
    def __init__(self, first_value=None, rows=None):
        self._first_value = first_value
        self._rows = [] if rows is None else rows

    def first(self):
        return self._first_value

    def all(self):
        return self._rows


class _DummySession:
    def __init__(self, result):
        self.received = None
        self._result = result

    async def execute(self, stmt):
        self.received = stmt
        return self._result


def test_derive_test_status_variants():
    assert svc.derive_test_status(None, None, None) is None
    assert svc.derive_test_status(1, 0, {}) == "passed"
    assert svc.derive_test_status(None, 2, {}) == "failed"
    assert svc.derive_test_status(None, None, {"timeout": True}) == "timeout"
    assert svc.derive_test_status(None, None, {"status": "error"}) == "error"


def test_parse_test_output_fallback():
    assert svc.parse_test_output(None) is None
    assert svc.parse_test_output("not-json") == "not-json"
    assert svc.parse_test_output('{"a": 1}') == {"a": 1}


@pytest.mark.asyncio
async def test_fetch_detail_not_found_raises(monkeypatch):
    with pytest.raises(Exception) as excinfo:
        await svc.fetch_detail(
            _DummySession(_DummyResult(first_value=None)),
            submission_id=1,
            talent_partner_id=2,
        )
    assert excinfo.value.status_code == 404


@pytest.mark.asyncio
async def test_fetch_detail_returns_row(monkeypatch):
    expected = ("sub", "task", "cs", SimpleNamespace(company_id=1, created_by=2))
    row = await svc.fetch_detail(
        _DummySession(_DummyResult(first_value=expected)),
        submission_id=1,
        talent_partner_id=2,
    )
    assert row == expected


@pytest.mark.asyncio
async def test_fetch_detail_rejects_wrong_company():
    expected = ("sub", "task", "cs", SimpleNamespace(company_id=7, created_by=2))
    with pytest.raises(Exception) as excinfo:
        await svc.fetch_detail(
            _DummySession(_DummyResult(first_value=expected)),
            submission_id=1,
            talent_partner_id=2,
            talent_partner_company_id=3,
        )
    assert excinfo.value.status_code == 403


@pytest.mark.asyncio
async def test_fetch_detail_allows_same_company():
    expected = ("sub", "task", "cs", SimpleNamespace(company_id=7, created_by=2))
    row = await svc.fetch_detail(
        _DummySession(_DummyResult(first_value=expected)),
        submission_id=1,
        talent_partner_id=99,
        talent_partner_company_id=7,
    )
    assert row == expected


@pytest.mark.asyncio
async def test_fetch_detail_rejects_wrong_owner_without_company_scope():
    expected = ("sub", "task", "cs", SimpleNamespace(company_id=7, created_by=99))
    with pytest.raises(Exception) as excinfo:
        await svc.fetch_detail(
            _DummySession(_DummyResult(first_value=expected)),
            submission_id=1,
            talent_partner_id=2,
            talent_partner_company_id=None,
        )
    assert excinfo.value.status_code == 404


def test_parse_test_output_non_dict_json():
    assert svc.parse_test_output("[]") == "[]"


@pytest.mark.asyncio
async def test_list_submissions_applies_filters():
    session = _DummySession(_DummyResult(rows=[("row",)]))
    rows = await svc.list_submissions(session, 1, candidate_session_id=2, task_id=3)
    assert rows == [("row",)]
    assert session.received is not None


@pytest.mark.asyncio
async def test_list_submissions_with_limit_offset():
    session = _DummySession(_DummyResult(rows=[]))
    rows = await svc.list_submissions(
        session, 1, candidate_session_id=None, task_id=None, limit=1, offset=1
    )
    assert rows == []
    assert session.received is not None
