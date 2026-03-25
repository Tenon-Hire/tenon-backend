from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from app.evaluations.services import (
    evaluations_services_evaluations_fit_profile_access_service as fit_profile_access,
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
async def test_fit_profile_access_lookup_and_company_access():
    missing_context = await fit_profile_access.get_candidate_session_evaluation_context(
        _FakeAccessDB(None),
        candidate_session_id=123,
    )
    assert missing_context is None

    row_context = await fit_profile_access.get_candidate_session_evaluation_context(
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
    assert row_context.simulation.id == 2
    assert row_context.scenario_version.id == 4

    assert (
        fit_profile_access.has_company_access(
            simulation_company_id=10, expected_company_id=None
        )
        is True
    )
    assert (
        fit_profile_access.has_company_access(
            simulation_company_id=10, expected_company_id=99
        )
        is False
    )
