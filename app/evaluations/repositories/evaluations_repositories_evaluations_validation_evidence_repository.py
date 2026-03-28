"""Application module for evaluations repositories evaluations validation evidence repository workflows."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse


class EvidencePointerValidationError(ValueError):
    """Raised when evidence_pointers_json payload shape is invalid."""


def _coerce_non_negative_int(value: Any, *, field_path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise EvidencePointerValidationError(f"{field_path} must be an integer.")
    if value < 0:
        raise EvidencePointerValidationError(f"{field_path} must be non-negative.")
    return value


def _validate_url(value: Any, *, field_path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvidencePointerValidationError(
            f"{field_path} must be a non-empty string."
        )
    normalized = value.strip()
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise EvidencePointerValidationError(
            f"{field_path} must be an http or https URL."
        )
    return normalized


def validate_evidence_pointers(value: Any) -> list[dict[str, Any]]:
    """Validate evidence pointers."""
    if not isinstance(value, list):
        raise EvidencePointerValidationError("evidence_pointers_json must be a list.")
    normalized: list[dict[str, Any]] = []
    for idx, pointer in enumerate(value):
        field_path = f"evidence_pointers_json[{idx}]"
        if not isinstance(pointer, Mapping):
            raise EvidencePointerValidationError(f"{field_path} must be an object.")
        item = dict(pointer)
        kind_raw = item.get("kind")
        if not isinstance(kind_raw, str) or not kind_raw.strip():
            raise EvidencePointerValidationError(
                f"{field_path}.kind must be a non-empty string."
            )
        kind = kind_raw.strip()
        item["kind"] = kind
        if "url" in item and item["url"] is not None:
            item["url"] = _validate_url(item["url"], field_path=f"{field_path}.url")
        if (
            "excerpt" in item
            and item["excerpt"] is not None
            and not isinstance(item["excerpt"], str)
        ):
            raise EvidencePointerValidationError(
                f"{field_path}.excerpt must be a string when provided."
            )
        if kind == "transcript":
            start_ms = _coerce_non_negative_int(
                item.get("startMs"), field_path=f"{field_path}.startMs"
            )
            end_ms = _coerce_non_negative_int(
                item.get("endMs"), field_path=f"{field_path}.endMs"
            )
            if end_ms < start_ms:
                raise EvidencePointerValidationError(
                    f"{field_path}.endMs must be greater than or equal to startMs."
                )
            item["startMs"] = start_ms
            item["endMs"] = end_ms
        if kind == "commit":
            ref_value = item.get("ref")
            if not isinstance(ref_value, str) or not ref_value.strip():
                raise EvidencePointerValidationError(
                    f"{field_path}.ref must be a non-empty string."
                )
            item["ref"] = ref_value.strip()
        normalized.append(item)
    return normalized
