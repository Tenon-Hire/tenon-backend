from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from app.evaluations.services import (
    evaluations_services_evaluations_winoe_report_access_service as winoe_report_access,
)


@dataclass
class _ExecuteFirstResult:
    value: object

    def first(self):
        return self.value


class _FakeAccessDB:
    def __init__(self, row):
        self._row = row

    async def execute(self, *_args, **_kwargs):
        return _ExecuteFirstResult(self._row)


@pytest.mark.asyncio
async def test_winoe_report_access_lookup_and_company_access():
    missing_context = (
        await winoe_report_access.get_candidate_session_evaluation_context(
            _FakeAccessDB(None),
            candidate_session_id=123,
        )
    )
    assert missing_context is None

    row_context = await winoe_report_access.get_candidate_session_evaluation_context(
        _FakeAccessDB(
            (
                SimpleNamespace(id=1),
                SimpleNamespace(id=2, company_id=3),
                SimpleNamespace(id=4),
            )
        ),
        candidate_session_id=123,
    )
    assert row_context is not None
    assert row_context.candidate_session.id == 1
    assert row_context.trial.id == 2
    assert row_context.scenario_version.id == 4

    assert (
        winoe_report_access.has_company_access(
            trial_company_id=10, expected_company_id=None
        )
        is True
    )
    assert (
        winoe_report_access.has_company_access(
            trial_company_id=10, expected_company_id=99
        )
        is False
    )
