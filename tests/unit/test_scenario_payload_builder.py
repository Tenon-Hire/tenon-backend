from __future__ import annotations

from types import SimpleNamespace

from app.services.simulations.scenario_payload_builder import (
    build_scenario_generation_payload,
)


def test_build_scenario_generation_payload_includes_recruiter_context_fields() -> None:
    simulation = SimpleNamespace(
        id=42,
        template_key="python-fastapi",
        scenario_template="default-5day-node-postgres",
        seniority="Mid",
        focus="Emphasize docs and test discipline.",
        company_context={"domain": "social", "productArea": "creator tools"},
        ai_notice_version="mvp1",
        ai_notice_text="AI may be used for scenario generation.",
        ai_eval_enabled_by_day={1: True, "2": True, "3": False, "9": True},
    )

    payload = build_scenario_generation_payload(simulation)

    assert payload["simulationId"] == 42
    assert payload["templateKey"] == "python-fastapi"
    assert payload["scenarioTemplate"] == "default-5day-node-postgres"
    assert payload["recruiterContext"]["seniority"] == "mid"
    assert payload["recruiterContext"]["focus"] == simulation.focus
    assert payload["recruiterContext"]["companyContext"] == simulation.company_context
    assert payload["recruiterContext"]["ai"] == {
        "noticeVersion": "mvp1",
        "noticeText": "AI may be used for scenario generation.",
        "evalEnabledByDay": {
            "1": True,
            "2": True,
            "3": False,
            "4": True,
            "5": True,
        },
    }
