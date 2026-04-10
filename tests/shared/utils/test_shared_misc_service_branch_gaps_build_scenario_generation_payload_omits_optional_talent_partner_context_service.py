from __future__ import annotations

from tests.shared.utils.shared_misc_service_branch_gaps_utils import *


def test_build_scenario_generation_payload_omits_optional_talent_partner_context(
    monkeypatch,
):
    trial = SimpleNamespace(
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
        "build_trial_company_context",
        lambda _value: None,
    )
    monkeypatch.setattr(
        scenario_payload_builder,
        "build_trial_ai_config",
        lambda **_kwargs: None,
    )

    payload = scenario_payload_builder.build_scenario_generation_payload(trial)

    assert payload["trialId"] == 1
    assert payload["talentPartnerContext"] == {}
