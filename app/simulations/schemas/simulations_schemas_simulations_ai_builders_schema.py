"""Application module for simulations schemas simulations ai builders schema workflows."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from app.simulations.constants.simulations_constants_simulations_ai_config_constants import (
    AI_NOTICE_DEFAULT_TEXT,
    AI_NOTICE_DEFAULT_VERSION,
    default_ai_eval_enabled_by_day,
)
from app.simulations.schemas.simulations_schemas_simulations_ai_models_schema import (
    SimulationAIConfig,
    SimulationCompanyContext,
)
from app.simulations.schemas.simulations_schemas_simulations_ai_values_schema import (
    resolve_simulation_ai_fields,
)


def build_simulation_company_context(value: Any) -> SimulationCompanyContext | None:
    """Build simulation company context."""
    if not isinstance(value, Mapping):
        return None
    try:
        return SimulationCompanyContext.model_validate(dict(value))
    except ValidationError:
        return None


def build_simulation_ai_config(
    *,
    notice_version: str | None,
    notice_text: str | None,
    eval_enabled_by_day: Any,
) -> SimulationAIConfig | None:
    """Build simulation ai config."""
    (
        resolved_notice_version,
        resolved_notice_text,
        resolved_eval,
    ) = resolve_simulation_ai_fields(
        notice_version=notice_version,
        notice_text=notice_text,
        eval_enabled_by_day=eval_enabled_by_day,
    )
    try:
        return SimulationAIConfig.model_validate(
            {
                "noticeVersion": resolved_notice_version,
                "noticeText": resolved_notice_text,
                "evalEnabledByDay": resolved_eval,
            }
        )
    except ValidationError:
        return SimulationAIConfig.model_validate(
            {
                "noticeVersion": AI_NOTICE_DEFAULT_VERSION,
                "noticeText": AI_NOTICE_DEFAULT_TEXT,
                "evalEnabledByDay": default_ai_eval_enabled_by_day(),
            }
        )


__all__ = ["build_simulation_ai_config", "build_simulation_company_context"]
