"""Application module for submissions services precommit bundle runtime submissions precommit bundle runtime core model workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

PRECOMMIT_MARKER_PREFIX = "tenon-precommit-bundle"
MAX_MARKER_SCAN_COMMITS = 50
DEFAULT_PRECOMMIT_BRANCH = "main"


@dataclass(slots=True)
class PrecommitBundleApplyResult:
    """Represent precommit bundle apply result data and behavior."""

    state: str
    precommit_sha: str | None
    bundle_id: int | None
    details: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class BundleFileChange:
    """Represent bundle file change data and behavior."""

    path: str
    content: str | None
    delete: bool
    executable: bool


@dataclass(slots=True)
class BundleLookupContext:
    """Represent bundle lookup context data and behavior."""

    candidate_session_id: Any
    scenario_version_id: int
    task_id: Any
    task_type: str
    repo_full_name: str
    default_branch: str
    template_key: str
    bundle: Any
    bundle_id: int


__all__ = [
    "BundleFileChange",
    "BundleLookupContext",
    "DEFAULT_PRECOMMIT_BRANCH",
    "MAX_MARKER_SCAN_COMMITS",
    "PRECOMMIT_MARKER_PREFIX",
    "PrecommitBundleApplyResult",
]
