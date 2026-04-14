from __future__ import annotations

import sys
import types

import pytest
from pydantic import BaseModel

from app.ai import ScenarioGenerationOutput
from app.ai.ai_provider_clients_service import (
    AIProviderExecutionError,
    _openai_schema_validation_error,
    _schema_payload,
    call_anthropic_json,
    call_openai_json_schema,
)


class _NestedConfig(BaseModel):
    label: str


class _ChildItem(BaseModel):
    name: str
    config: _NestedConfig


class _RootPayload(BaseModel):
    title: str
    child: _ChildItem
    items: list[_ChildItem]
    metadata: dict[str, object]


class _TinyResponse(BaseModel):
    message: str


def _scenario_generation_payload(
    *, include_required_fields: bool = True
) -> dict[str, object]:
    payload: dict[str, object] = {
        "storyline_md": "A concise but realistic Winoe scenario.",
        "task_prompts_json": [
            {
                "dayIndex": day_index,
                "title": f"Day {day_index}",
                "description": f"Deliverable for day {day_index}.",
            }
            for day_index in range(1, 6)
        ],
    }
    if include_required_fields:
        payload["rubric_json"] = {
            "summary": "Concise rubric summary.",
            "dayWeights": {"1": 10, "2": 20, "3": 30, "4": 20, "5": 20},
            "dimensions": [
                {
                    "name": "Planning",
                    "weight": 40,
                    "description": "Plans the work well.",
                },
                {
                    "name": "Execution",
                    "weight": 60,
                    "description": "Delivers the work cleanly.",
                },
            ],
        }
        payload["codespace_spec_json"] = {
            "task_kind": "feature",
            "summary": "Build the Winoe feature.",
            "candidate_goal": "Implement the required backend changes.",
            "acceptance_criteria": [
                "The endpoint works.",
                "The data is persisted correctly.",
            ],
            "target_files": ["app/example.py"],
            "repo_adjustments": ["Add route and service logic"],
            "test_focus": ["happy path", "failure path"],
            "test_command": "poetry run pytest tests/example",
        }
    return payload


def test_schema_payload_sets_additional_properties_false_recursively() -> None:
    schema = _schema_payload(_RootPayload)

    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert schema["required"] == ["title", "child", "items", "metadata"]

    defs = schema["$defs"]
    assert defs["_NestedConfig"]["additionalProperties"] is False
    assert defs["_NestedConfig"]["required"] == ["label"]
    assert defs["_ChildItem"]["additionalProperties"] is False
    assert defs["_ChildItem"]["required"] == ["name", "config"]

    child_property = schema["properties"]["child"]
    assert child_property["$ref"] == "#/$defs/_ChildItem"

    item_schema = schema["properties"]["items"]["items"]
    assert item_schema["$ref"] == "#/$defs/_ChildItem"

    metadata_schema = schema["properties"]["metadata"]
    assert metadata_schema["type"] == "object"
    assert metadata_schema["additionalProperties"] is False
    assert metadata_schema["required"] == []


def test_openai_schema_validation_error_detector_matches_provider_message() -> None:
    exc = RuntimeError(
        "Error code: 400 - {'error': {'code': 'invalid_json_schema', 'message': 'Invalid schema for response_format'}}"
    )

    assert _openai_schema_validation_error(exc) is True


def test_scenario_generation_output_schema_is_strictly_openai_compatible() -> None:
    schema = _schema_payload(ScenarioGenerationOutput)

    rubric_schema = schema["$defs"]["ScenarioRubric"]
    weights_schema = schema["$defs"]["ScenarioRubricDayWeights"]

    assert rubric_schema["additionalProperties"] is False
    assert rubric_schema["required"] == ["summary", "dayWeights", "dimensions"]
    assert weights_schema["additionalProperties"] is False
    assert weights_schema["required"] == ["1", "2", "3", "4", "5"]


def test_call_openai_json_schema_passes_bounded_reasoning_controls(monkeypatch) -> None:
    class _FakeResponses:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            return types.SimpleNamespace(output_text='{"message":"ok"}')

    class _FakeOpenAI:
        last_client = None

        def __init__(self, *, api_key, timeout, max_retries) -> None:
            self.api_key = api_key
            self.timeout = timeout
            self.max_retries = max_retries
            self.responses = _FakeResponses()
            _FakeOpenAI.last_client = self

    monkeypatch.setitem(
        sys.modules, "openai", types.SimpleNamespace(OpenAI=_FakeOpenAI)
    )

    result = call_openai_json_schema(
        api_key="test-key",
        model="gpt-5.4-mini",
        system_prompt="system",
        user_prompt="user",
        response_model=_TinyResponse,
        timeout_seconds=45,
        max_retries=1,
        max_output_tokens=321,
        reasoning_effort="minimal",
        text_verbosity="low",
        temperature=0,
    )

    assert result.message == "ok"

    client = _FakeOpenAI.last_client
    assert client is not None
    assert client.api_key == "test-key"
    assert client.timeout == 45
    assert client.max_retries == 1

    request = client.responses.calls[0]
    assert request["max_output_tokens"] == 321
    assert request["reasoning"] == {"effort": "none"}
    assert request["text"]["verbosity"] == "low"
    assert request["temperature"] == 0


def test_call_anthropic_json_prefers_tool_schema_output(monkeypatch) -> None:
    class _FakeBlock:
        def __init__(
            self, *, block_type: str, input_payload=None, text: str = ""
        ) -> None:
            self.type = block_type
            self.input = input_payload
            self.text = text

    class _FakeMessages:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            return types.SimpleNamespace(
                content=[
                    _FakeBlock(block_type="tool_use", input_payload={"message": "ok"})
                ]
            )

    class _FakeAnthropic:
        last_client = None

        def __init__(self, *, api_key, timeout, max_retries) -> None:
            self.api_key = api_key
            self.timeout = timeout
            self.max_retries = max_retries
            self.messages = _FakeMessages()
            _FakeAnthropic.last_client = self

    monkeypatch.setitem(
        sys.modules, "anthropic", types.SimpleNamespace(Anthropic=_FakeAnthropic)
    )

    result = call_anthropic_json(
        api_key="test-key",
        model="claude-sonnet-4-6",
        system_prompt="system",
        user_prompt="user",
        response_model=_TinyResponse,
        timeout_seconds=30,
        max_retries=1,
        max_tokens=128,
    )

    assert result.message == "ok"

    client = _FakeAnthropic.last_client
    assert client is not None
    request = client.messages.calls[0]
    assert request["tool_choice"] == {"type": "tool", "name": "_TinyResponse"}
    assert request["tools"][0]["name"] == "_TinyResponse"


def test_call_anthropic_json_validates_complete_tool_payload(monkeypatch) -> None:
    class _FakeBlock:
        def __init__(self, *, block_type: str, input_payload=None) -> None:
            self.type = block_type
            self.input = input_payload

    class _FakeMessages:
        def create(self, **kwargs):
            return types.SimpleNamespace(
                content=[
                    _FakeBlock(
                        block_type="tool_use",
                        input_payload=_scenario_generation_payload(),
                    )
                ]
            )

    class _FakeAnthropic:
        def __init__(self, *, api_key, timeout, max_retries) -> None:
            self.api_key = api_key
            self.timeout = timeout
            self.max_retries = max_retries
            self.messages = _FakeMessages()

    monkeypatch.setitem(
        sys.modules, "anthropic", types.SimpleNamespace(Anthropic=_FakeAnthropic)
    )

    result = call_anthropic_json(
        api_key="test-key",
        model="claude-opus-4-6",
        system_prompt="system",
        user_prompt="user",
        response_model=ScenarioGenerationOutput,
        timeout_seconds=30,
        max_retries=1,
        max_tokens=512,
    )

    assert result.storyline_md == "A concise but realistic Winoe scenario."
    assert len(result.task_prompts_json) == 5
    assert result.rubric_json.summary == "Concise rubric summary."
    assert result.codespace_spec_json.summary == "Build the Winoe feature."


def test_call_anthropic_json_rejects_partial_tool_payload(monkeypatch) -> None:
    class _FakeBlock:
        def __init__(self, *, block_type: str, input_payload=None) -> None:
            self.type = block_type
            self.input = input_payload

    class _FakeMessages:
        def create(self, **kwargs):
            return types.SimpleNamespace(
                content=[
                    _FakeBlock(
                        block_type="tool_use",
                        input_payload=_scenario_generation_payload(
                            include_required_fields=False
                        ),
                    )
                ]
            )

    class _FakeAnthropic:
        def __init__(self, *, api_key, timeout, max_retries) -> None:
            self.api_key = api_key
            self.timeout = timeout
            self.max_retries = max_retries
            self.messages = _FakeMessages()

    monkeypatch.setitem(
        sys.modules, "anthropic", types.SimpleNamespace(Anthropic=_FakeAnthropic)
    )

    with pytest.raises(AIProviderExecutionError, match="anthropic_invalid_json_output"):
        call_anthropic_json(
            api_key="test-key",
            model="claude-opus-4-6",
            system_prompt="system",
            user_prompt="user",
            response_model=ScenarioGenerationOutput,
            timeout_seconds=30,
            max_retries=1,
            max_tokens=512,
        )
