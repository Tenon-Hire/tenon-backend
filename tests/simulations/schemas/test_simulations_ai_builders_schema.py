from __future__ import annotations

from app.simulations.constants.simulations_constants_simulations_ai_config_constants import (
    AI_NOTICE_DEFAULT_TEXT,
    AI_NOTICE_DEFAULT_VERSION,
    default_ai_eval_enabled_by_day,
)
from app.simulations.schemas import (
    simulations_schemas_simulations_ai_builders_schema as ai_builders,
)


def test_build_simulation_company_context_handles_success_and_invalid_shapes():
    assert ai_builders.build_simulation_company_context("not-a-map") is None
    assert ai_builders.build_simulation_company_context({"unknown": "value"}) is None

    context = ai_builders.build_simulation_company_context(
        {"domain": "healthcare", "productArea": "operations"}
    )
    assert context is not None
    assert context.domain == "healthcare"
    assert context.product_area == "operations"


def test_build_simulation_ai_config_returns_valid_resolved_config(monkeypatch):
    monkeypatch.setattr(
        ai_builders,
        "resolve_simulation_ai_fields",
        lambda **_kwargs: (
            "mvp-custom",
            "custom notice",
            {"1": True, "2": False, "3": True, "4": False, "5": True},
        ),
    )

    config = ai_builders.build_simulation_ai_config(
        notice_version=None,
        notice_text=None,
        eval_enabled_by_day=None,
    )
    assert config is not None
    assert config.notice_version == "mvp-custom"
    assert config.notice_text == "custom notice"
    assert config.eval_enabled_by_day == {
        "1": True,
        "2": False,
        "3": True,
        "4": False,
        "5": True,
    }


def test_build_simulation_ai_config_falls_back_when_resolved_values_do_not_validate(
    monkeypatch,
):
    monkeypatch.setattr(
        ai_builders,
        "resolve_simulation_ai_fields",
        lambda **_kwargs: ("mvp-custom", "custom notice", {"1": "not-a-bool"}),
    )

    config = ai_builders.build_simulation_ai_config(
        notice_version="mvp-custom",
        notice_text="custom notice",
        eval_enabled_by_day={"1": False},
    )
    assert config is not None
    assert config.notice_version == AI_NOTICE_DEFAULT_VERSION
    assert config.notice_text == AI_NOTICE_DEFAULT_TEXT
    assert config.eval_enabled_by_day == default_ai_eval_enabled_by_day()
