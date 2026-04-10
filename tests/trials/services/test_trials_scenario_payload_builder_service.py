from __future__ import annotations

from types import SimpleNamespace

from app.trials.services.trials_services_trials_scenario_payload_builder_service import (
    build_scenario_generation_payload,
)


def test_build_scenario_generation_payload_includes_talent_partner_context_fields() -> (
    None
):
    trial = SimpleNamespace(
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

    payload = build_scenario_generation_payload(trial)

    assert payload["trialId"] == 42
    assert payload["templateKey"] == "python-fastapi"
    assert payload["scenarioTemplate"] == "default-5day-node-postgres"
    assert payload["talentPartnerContext"]["seniority"] == "mid"
    assert payload["talentPartnerContext"]["focus"] == trial.focus
    assert payload["talentPartnerContext"]["companyContext"] == trial.company_context
    assert payload["talentPartnerContext"]["ai"] == {
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
