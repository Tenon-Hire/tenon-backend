from __future__ import annotations

from tests.shared.utils.shared_misc_service_branch_gaps_utils import *


def test_build_scenario_generation_payload_omits_optional_recruiter_context(
    monkeypatch,
):
    simulation = SimpleNamespace(
        id=1,
        template_key="python-fastapi",
        scenario_template="backend",
        seniority=None,
        focus=None,
        company_context=None,
        ai_notice_version=None,
        ai_notice_text=None,
        ai_eval_enabled_by_day=None,
    )

    monkeypatch.setattr(
        scenario_payload_builder, "normalize_role_level", lambda _value: None
    )
    monkeypatch.setattr(
        scenario_payload_builder,
        "build_simulation_company_context",
        lambda _value: None,
    )
    monkeypatch.setattr(
        scenario_payload_builder,
        "build_simulation_ai_config",
        lambda **_kwargs: None,
    )

    payload = scenario_payload_builder.build_scenario_generation_payload(simulation)

    assert payload["simulationId"] == 1
    assert payload["recruiterContext"] == {}
