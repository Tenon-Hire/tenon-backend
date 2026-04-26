from __future__ import annotations

import pytest

from app.integrations.scenario_generation.anthropic_provider_client import (
    AnthropicScenarioGenerationProvider,
)
from app.integrations.scenario_generation.factory_client import (
    get_scenario_generation_provider,
)
from app.integrations.scenario_generation.openai_provider_client import (
    OpenAIScenarioGenerationProvider,
)
from app.integrations.winoe_report_review.anthropic_provider_client import (
    AnthropicWinoeReportReviewProvider,
)
from app.integrations.winoe_report_review.factory_client import (
    get_winoe_report_review_provider,
)
from app.integrations.winoe_report_review.openai_provider_client import (
    OpenAIWinoeReportReviewProvider,
)


def test_scenario_generation_provider_factory_branches():
    get_scenario_generation_provider.cache_clear()
    assert isinstance(
        get_scenario_generation_provider(" anthropic "),
        AnthropicScenarioGenerationProvider,
    )
    assert isinstance(
        get_scenario_generation_provider("openai"),
        OpenAIScenarioGenerationProvider,
    )
    with pytest.raises(ValueError):
        get_scenario_generation_provider("unsupported")


def test_winoe_report_review_provider_factory_branches():
    get_winoe_report_review_provider.cache_clear()
    assert isinstance(
        get_winoe_report_review_provider(" anthropic "),
        AnthropicWinoeReportReviewProvider,
    )
    assert isinstance(
        get_winoe_report_review_provider("openai"),
        OpenAIWinoeReportReviewProvider,
    )
    with pytest.raises(ValueError):
        get_winoe_report_review_provider("unsupported")
