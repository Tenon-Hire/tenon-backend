"""Anthropic-backed codespace-specializer provider."""

from __future__ import annotations

from app.ai import CodespacePatchProposal
from app.ai.ai_provider_clients_service import (
    AIProviderExecutionError,
    call_anthropic_json,
)
from app.config import settings
from app.integrations.codespace_specializer.base_client import (
    CodespaceSpecializerProviderError,
    CodespaceSpecializerRequest,
    CodespaceSpecializerResponse,
)


class AnthropicCodespaceSpecializerProvider:
    """Generate codespace-specializer diffs with Anthropic JSON responses."""

    def specialize_codespace(
        self,
        *,
        request: CodespaceSpecializerRequest,
    ) -> CodespaceSpecializerResponse:
        try:
            result = call_anthropic_json(
                api_key=settings.ANTHROPIC_API_KEY,
                model=request.model,
                system_prompt=request.system_prompt,
                user_prompt=request.user_prompt,
                response_model=CodespacePatchProposal,
                timeout_seconds=settings.CODESPACE_SPECIALIZER_TIMEOUT_SECONDS,
                max_retries=settings.CODESPACE_SPECIALIZER_MAX_RETRIES,
            )
        except AIProviderExecutionError as exc:
            raise CodespaceSpecializerProviderError(str(exc)) from exc
        return CodespaceSpecializerResponse(
            result=result,
            model_name=request.model,
            model_version=request.model,
        )


__all__ = ["AnthropicCodespaceSpecializerProvider"]
