from __future__ import annotations

SCENARIO_GENERATION_JOB_TYPE = "scenario_generation"
SCENARIO_PROMPT_VERSION = "scenario-generation-v1"
SCENARIO_RUBRIC_VERSION = "scenario-rubric-v1"
FALLBACK_MODEL_NAME = "template_catalog_fallback"
FALLBACK_MODEL_VERSION = "v1"
SCENARIO_SOURCE_LLM = "llm"
SCENARIO_SOURCE_TEMPLATE_FALLBACK = "template_fallback"

OPENAI_API_ENV_KEYS = ("WINOE_OPENAI_API_KEY", "OPENAI_API_KEY")
ANTHROPIC_API_ENV_KEYS = ("WINOE_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY")
DEMO_MODE_ENV_KEYS = ("WINOE_DEMO_MODE", "WINOE_SCENARIO_DEMO_MODE")

STORYLINE_CONTEXTS = (
    "a monetization feature with strict reporting accuracy requirements",
    "an incident-prone integration that needs stronger reliability boundaries",
    "a high-volume workflow where latency spikes directly impact conversion",
    "a migration effort balancing delivery speed and production safety",
    "a compliance-sensitive release with explicit auditability expectations",
)
STORYLINE_CONSTRAINTS = (
    "tight operational observability from day one",
    "clear rollback paths for every risky change",
    "small, testable increments that can ship safely",
    "explicit failure-mode handling and graceful degradation",
    "well-scoped interfaces so ownership stays clear",
)
CODE_PRIORITIES = (
    "correctness under realistic edge cases",
    "testability and maintainable abstractions",
    "performance-sensitive database access patterns",
    "defensive validation and error handling",
    "traceable behavior with useful diagnostics",
)
DEBUG_SIGNALS = (
    "a flaky production-like test signal",
    "an intermittent regression after a recent refactor",
    "inconsistent behavior across environments",
    "a correctness bug hidden by shallow happy-path tests",
    "a state-management bug triggered by retry paths",
)

__all__ = [
    "ANTHROPIC_API_ENV_KEYS",
    "CODE_PRIORITIES",
    "DEBUG_SIGNALS",
    "DEMO_MODE_ENV_KEYS",
    "FALLBACK_MODEL_NAME",
    "FALLBACK_MODEL_VERSION",
    "OPENAI_API_ENV_KEYS",
    "SCENARIO_GENERATION_JOB_TYPE",
    "SCENARIO_PROMPT_VERSION",
    "SCENARIO_RUBRIC_VERSION",
    "SCENARIO_SOURCE_LLM",
    "SCENARIO_SOURCE_TEMPLATE_FALLBACK",
    "STORYLINE_CONSTRAINTS",
    "STORYLINE_CONTEXTS",
]
