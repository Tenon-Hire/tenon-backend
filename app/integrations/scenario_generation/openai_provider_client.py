"""OpenAI-backed scenario-generation provider."""

from __future__ import annotations

from app.ai import ScenarioGenerationOutput
from app.ai.ai_provider_clients_service import (
    AIProviderExecutionError,
    call_openai_json_schema,
)
from app.config import settings
from app.integrations.scenario_generation.base_client import (
    ScenarioGenerationProviderError,
    ScenarioGenerationProviderRequest,
    ScenarioGenerationProviderResponse,
)


class OpenAIScenarioGenerationProvider:
    """Generate scenarios with OpenAI structured outputs."""

    def generate_scenario(
        self,
        *,
        request: ScenarioGenerationProviderRequest,
    ) -> ScenarioGenerationProviderResponse:
        try:
            result = call_openai_json_schema(
                api_key=settings.OPENAI_API_KEY,
                model=request.model,
                system_prompt=request.system_prompt,
                user_prompt=request.user_prompt,
                response_model=ScenarioGenerationOutput,
                timeout_seconds=settings.SCENARIO_GENERATION_TIMEOUT_SECONDS,
                max_retries=settings.SCENARIO_GENERATION_MAX_RETRIES,
            )
        except AIProviderExecutionError as exc:
            raise ScenarioGenerationProviderError(str(exc)) from exc
        return ScenarioGenerationProviderResponse(
            result=result,
            model_name=request.model,
            model_version=request.model,
        )


__all__ = ["OpenAIScenarioGenerationProvider"]
