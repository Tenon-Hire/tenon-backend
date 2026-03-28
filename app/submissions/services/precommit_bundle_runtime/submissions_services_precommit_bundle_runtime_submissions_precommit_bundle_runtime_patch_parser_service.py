"""Application module for submissions services precommit bundle runtime submissions precommit bundle runtime patch parser service workflows."""

from __future__ import annotations

import json

from app.shared.utils.shared_utils_errors_utils import ApiError
from app.submissions.services.precommit_bundle_runtime.submissions_services_precommit_bundle_runtime_submissions_precommit_bundle_runtime_core_model import (
    BundleFileChange,
)


def parse_patch_entries(
    *, patch_text: str | None, storage_ref: str | None
) -> list[BundleFileChange]:
    """Parse patch entries."""
    if patch_text is None:
        raise ApiError(
            status_code=500,
            detail="Precommit bundle storage_ref-only payloads are not supported yet.",
            error_code="PRECOMMIT_STORAGE_REF_UNSUPPORTED",
            details={"storageRef": storage_ref},
        )
    try:
        parsed = json.loads(patch_text)
    except ValueError as exc:
        raise ApiError(
            status_code=500,
            detail="Precommit bundle patch payload is invalid JSON.",
            error_code="PRECOMMIT_PATCH_INVALID_JSON",
        ) from exc

    entries_raw = parsed.get("files") if isinstance(parsed, dict) else parsed
    if not isinstance(entries_raw, list):
        raise ApiError(
            status_code=500,
            detail="Precommit bundle patch payload must contain a file list.",
            error_code="PRECOMMIT_PATCH_INVALID_FORMAT",
        )

    changes: list[BundleFileChange] = []
    for idx, raw_entry in enumerate(entries_raw):
        if not isinstance(raw_entry, dict):
            raise ApiError(
                status_code=500,
                detail="Precommit bundle patch entry must be an object.",
                error_code="PRECOMMIT_PATCH_INVALID_ENTRY",
                details={"entryIndex": idx},
            )
        path = _parse_path(raw_entry, idx)
        delete = bool(raw_entry.get("delete", False))
        executable = bool(raw_entry.get("executable", False))
        content = _parse_content(raw_entry, idx, path, delete)
        changes.append(
            BundleFileChange(
                path=path, content=content, delete=delete, executable=executable
            )
        )
    return changes


def _parse_path(raw_entry: dict[str, object], idx: int) -> str:
    raw_path = raw_entry.get("path")
    if not isinstance(raw_path, str):
        raise ApiError(
            status_code=500,
            detail="Precommit bundle path must be a string.",
            error_code="PRECOMMIT_PATCH_INVALID_PATH",
            details={"entryIndex": idx},
        )
    path = raw_path.strip()
    ensure_safe_repo_path(path)
    return path


def _parse_content(
    raw_entry: dict[str, object], idx: int, path: str, delete: bool
) -> str | None:
    if delete:
        return None
    raw_content = raw_entry.get("content")
    if not isinstance(raw_content, str):
        raise ApiError(
            status_code=500,
            detail="Precommit bundle content must be a string.",
            error_code="PRECOMMIT_PATCH_INVALID_CONTENT",
            details={"entryIndex": idx, "path": path},
        )
    return raw_content


def ensure_safe_repo_path(path: str) -> None:
    """Ensure safe repo path."""
    if not path:
        _raise_unsafe_path(path, "Precommit bundle path cannot be empty.")
    if path.startswith("/") or path.startswith("./") or path.startswith("../"):
        _raise_unsafe_path(
            path, "Precommit bundle path cannot be absolute or traversing."
        )
    if "\\" in path:
        _raise_unsafe_path(path, "Precommit bundle path must use POSIX separators.")
    parts = path.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        _raise_unsafe_path(path, "Precommit bundle path contains unsafe segments.")
    if parts[0] == ".git":
        _raise_unsafe_path(path, "Precommit bundle path cannot target .git internals.")


def _raise_unsafe_path(path: str, detail: str) -> None:
    raise ApiError(
        status_code=500,
        detail=detail,
        error_code="PRECOMMIT_PATCH_UNSAFE_PATH",
        details={"path": path},
    )
