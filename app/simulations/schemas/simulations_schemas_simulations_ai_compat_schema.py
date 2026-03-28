"""Application module for simulations schemas simulations ai compat schema workflows."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from app.simulations.constants.simulations_constants_simulations_ai_config_constants import (
    AI_NOTICE_DEFAULT_TEXT,
    AI_NOTICE_DEFAULT_VERSION,
    default_ai_eval_enabled_by_day,
)
from app.simulations.schemas.simulations_schemas_simulations_ai_models_schema import (
    SimulationAIConfig,
)

Resolver = Callable[..., tuple[str, str, dict[str, bool]]]


def build_simulation_ai_config_with_resolver(
    *,
    notice_version: str | None,
    notice_text: str | None,
    eval_enabled_by_day: Any,
    resolver: Resolver,
) -> SimulationAIConfig | None:
    """Build simulation ai config with resolver."""
    resolved_notice_version, resolved_notice_text, resolved_eval = resolver(
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


__all__ = ["build_simulation_ai_config_with_resolver"]
