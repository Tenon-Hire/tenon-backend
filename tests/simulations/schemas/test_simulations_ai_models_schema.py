from __future__ import annotations

from app.simulations.schemas.simulations_schemas_simulations_ai_models_schema import (
    SimulationAIConfig,
    SimulationCompanyContext,
)


def test_simulation_company_context_serializer_omits_none_fields():
    assert SimulationCompanyContext.model_validate({}).model_dump() == {}
    assert SimulationCompanyContext.model_validate(
        {"domain": "fintech"}
    ).model_dump() == {"domain": "fintech"}
    assert SimulationCompanyContext.model_validate(
        {"productArea": "payments"}
    ).model_dump() == {"productArea": "payments"}


def test_simulation_ai_config_serializer_omits_none_fields():
    assert SimulationAIConfig.model_validate({}).model_dump() == {}
    assert SimulationAIConfig.model_validate(
        {"noticeVersion": "mvp1"}
    ).model_dump() == {"noticeVersion": "mvp1"}
    assert SimulationAIConfig.model_validate({"noticeText": "notice"}).model_dump() == {
        "noticeText": "notice"
    }
    assert SimulationAIConfig.model_validate(
        {"evalEnabledByDay": {"1": True}}
    ).model_dump() == {"evalEnabledByDay": {"1": True}}
