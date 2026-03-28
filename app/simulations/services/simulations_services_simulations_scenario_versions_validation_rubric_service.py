"""Application module for simulations services simulations scenario versions validation rubric service workflows."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any

from app.simulations.schemas.simulations_schemas_simulations_core_schema import (
    MAX_SCENARIO_RUBRIC_BYTES,
)
from app.simulations.services.simulations_services_simulations_scenario_versions_validation_base_service import (
    json_payload_size_bytes,
    parse_positive_int,
    raise_patch_validation_error,
)


def validate_rubric(rubric_json: Any) -> dict[str, Any]:
    """Validate rubric."""
    if not isinstance(rubric_json, Mapping):
        raise_patch_validation_error(
            "rubric must be an object.",
            field="rubric",
        )
    normalized = copy.deepcopy(dict(rubric_json))
    size_bytes = json_payload_size_bytes(normalized)
    if size_bytes > MAX_SCENARIO_RUBRIC_BYTES:
        raise_patch_validation_error(
            f"rubric exceeds {MAX_SCENARIO_RUBRIC_BYTES} bytes.",
            field="rubric",
            details={"maxBytes": MAX_SCENARIO_RUBRIC_BYTES, "actualBytes": size_bytes},
        )
    _normalize_day_weights(normalized)
    _normalize_dimensions(normalized)
    return normalized


def _normalize_day_weights(normalized: dict[str, Any]) -> None:
    raw_weights = normalized.get("dayWeights")
    if raw_weights is None:
        return
    if not isinstance(raw_weights, Mapping):
        raise_patch_validation_error(
            "rubric.dayWeights must be an object when provided.",
            field="rubric",
        )
    parsed_weights: dict[str, int] = {}
    for raw_day, raw_weight in raw_weights.items():
        day_index = parse_positive_int(raw_day)
        weight = parse_positive_int(raw_weight)
        if day_index is None or weight is None:
            raise_patch_validation_error(
                "rubric.dayWeights must map positive day indices to positive integer weights.",
                field="rubric",
            )
        parsed_weights[str(day_index)] = weight
    normalized["dayWeights"] = parsed_weights


def _normalize_dimensions(normalized: dict[str, Any]) -> None:
    dimensions = normalized.get("dimensions")
    if dimensions is None:
        return
    if not isinstance(dimensions, list):
        raise_patch_validation_error(
            "rubric.dimensions must be an array when provided.",
            field="rubric",
        )
    normalized_dimensions: list[dict[str, Any]] = []
    for idx, dimension in enumerate(dimensions):
        normalized_dimensions.append(_normalize_dimension(dimension, idx))
    normalized["dimensions"] = normalized_dimensions


def _normalize_dimension(dimension: Any, idx: int) -> dict[str, Any]:
    if not isinstance(dimension, Mapping):
        raise_patch_validation_error(
            "Each rubric.dimensions item must be an object.",
            field="rubric",
            details={"index": idx},
        )
    item = dict(dimension)
    name = _required_non_empty_string(item.get("name"), idx, "name")
    description = _required_non_empty_string(
        item.get("description"), idx, "description"
    )
    weight = parse_positive_int(item.get("weight"))
    if weight is None:
        raise_patch_validation_error(
            "rubric.dimensions.weight must be a positive integer.",
            field="rubric",
            details={"index": idx},
        )
    item["name"] = name
    item["description"] = description
    item["weight"] = weight
    return item


def _required_non_empty_string(value: Any, idx: int, field_name: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise_patch_validation_error(
        f"rubric.dimensions.{field_name} must be a non-empty string.",
        field="rubric",
        details={"index": idx},
    )
