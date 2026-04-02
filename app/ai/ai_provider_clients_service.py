"""Low-level SDK helpers for OpenAI and Anthropic JSON generation."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel


class AIProviderExecutionError(RuntimeError):
    """Raised when an upstream AI provider call fails or returns invalid output."""


def api_key_configured(api_key: str | None) -> bool:
    """Return whether an API key is present and not just a placeholder."""
    normalized = (api_key or "").strip()
    return bool(normalized and normalized != "__REPLACE_ME__")


def _schema_payload(schema_model: type[BaseModel]) -> dict[str, Any]:
    return schema_model.model_json_schema()


def _extract_json_text(raw_text: str) -> str:
    text = raw_text.strip()
    if text.startswith("```"):
        fenced = re.sub(r"^```(?:json)?\s*", "", text)
        fenced = re.sub(r"\s*```$", "", fenced)
        text = fenced.strip()
    return text


def call_openai_json_schema(
    *,
    api_key: str | None,
    model: str,
    system_prompt: str,
    user_prompt: str,
    response_model: type[BaseModel],
    timeout_seconds: int,
    max_retries: int,
) -> BaseModel:
    """Call OpenAI Responses API with strict JSON-schema output."""
    if not api_key_configured(api_key):
        raise AIProviderExecutionError("missing_openai_api_key")
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise AIProviderExecutionError("openai_sdk_not_installed") from exc

    client = OpenAI(
        api_key=api_key,
        timeout=timeout_seconds,
        max_retries=max_retries,
    )
    try:
        response = client.responses.create(
            model=model,
            input=[
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": system_prompt}],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": user_prompt}],
                },
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": response_model.__name__,
                    "schema": _schema_payload(response_model),
                    "strict": True,
                }
            },
        )
    except Exception as exc:  # pragma: no cover - network/provider variability
        raise AIProviderExecutionError(
            f"openai_request_failed:{type(exc).__name__}"
        ) from exc

    output_text = getattr(response, "output_text", None)
    if not isinstance(output_text, str) or not output_text.strip():
        raise AIProviderExecutionError("openai_empty_structured_output")
    try:
        return response_model.model_validate_json(output_text)
    except Exception as exc:
        raise AIProviderExecutionError("openai_invalid_structured_output") from exc


def call_anthropic_json(
    *,
    api_key: str | None,
    model: str,
    system_prompt: str,
    user_prompt: str,
    response_model: type[BaseModel],
    timeout_seconds: int,
    max_retries: int,
    max_tokens: int = 4_096,
) -> BaseModel:
    """Call Anthropic Messages API and validate JSON output against a schema."""
    if not api_key_configured(api_key):
        raise AIProviderExecutionError("missing_anthropic_api_key")
    try:
        from anthropic import Anthropic
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise AIProviderExecutionError("anthropic_sdk_not_installed") from exc

    schema_json = json.dumps(_schema_payload(response_model), sort_keys=True)
    system_text = (
        f"{system_prompt.strip()}\n\n"
        "Return only one JSON object that matches this schema exactly.\n"
        f"{schema_json}"
    )
    client = Anthropic(
        api_key=api_key,
        timeout=timeout_seconds,
        max_retries=max_retries,
    )
    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=0,
            system=system_text,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except Exception as exc:  # pragma: no cover - network/provider variability
        raise AIProviderExecutionError(
            f"anthropic_request_failed:{type(exc).__name__}"
        ) from exc

    blocks = getattr(response, "content", [])
    text_parts = [
        getattr(block, "text", "")
        for block in blocks
        if getattr(block, "type", None) == "text"
    ]
    payload_text = _extract_json_text("\n".join(part for part in text_parts if part))
    if not payload_text:
        raise AIProviderExecutionError("anthropic_empty_json_output")
    try:
        return response_model.model_validate(json.loads(payload_text))
    except Exception as exc:
        raise AIProviderExecutionError("anthropic_invalid_json_output") from exc


__all__ = [
    "AIProviderExecutionError",
    "api_key_configured",
    "call_anthropic_json",
    "call_openai_json_schema",
]
