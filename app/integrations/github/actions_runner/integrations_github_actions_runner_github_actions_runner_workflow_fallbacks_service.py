"""Application module for integrations github actions runner github actions runner workflow fallbacks service workflows."""

from __future__ import annotations


def build_workflow_fallbacks(workflow_file: str) -> list[str]:
    """Build workflow fallbacks."""
    return list(
        dict.fromkeys([workflow_file, "winoe-ci.yml", ".github/workflows/winoe-ci.yml"])
    )
