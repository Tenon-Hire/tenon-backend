"""Application module for integrations github template health github template health live result model workflows."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LiveCheckResult:
    """Represent live check result data and behavior."""

    errors: list[str]
    workflow_run_id: int | None
    workflow_conclusion: str | None
    artifact_name_found: str | None
