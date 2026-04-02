"""Codespace-specializer provider contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.ai import CodespacePatchProposal


class CodespaceSpecializerProviderError(RuntimeError):
    """Raised when codespace-specializer provider execution fails."""


@dataclass(frozen=True, slots=True)
class CodespaceSpecializerRequest:
    """Structured prompt request for codespace specialization providers."""

    system_prompt: str
    user_prompt: str
    model: str


@dataclass(frozen=True, slots=True)
class CodespaceSpecializerResponse:
    """Structured provider response for codespace specialization."""

    result: CodespacePatchProposal
    model_name: str
    model_version: str


class CodespaceSpecializerProvider(Protocol):
    """Provider contract for template-repository specialization."""

    def specialize_codespace(
        self,
        *,
        request: CodespaceSpecializerRequest,
    ) -> CodespaceSpecializerResponse:
        """Return a patch proposal for a template repository."""
        ...


__all__ = [
    "CodespaceSpecializerProvider",
    "CodespaceSpecializerProviderError",
    "CodespaceSpecializerRequest",
    "CodespaceSpecializerResponse",
]
