from __future__ import annotations
# NOTE: Exceeds 50 LOC to keep cache management centralized for runner compatibility.
from collections import OrderedDict
from typing import Any

from app.domains.github_native.actions_runner.models import ActionsRunResult
from app.domains.github_native.artifacts import ParsedTestResults


class ActionsCache:
    """LRU caches for run and artifact lookups."""

    def __init__(self, max_entries: int = 128) -> None:
        self.max_entries = max_entries
        self.run_cache: OrderedDict[tuple[str, int], ActionsRunResult] = OrderedDict()
        self.artifact_cache: OrderedDict[
            tuple[str, int, int], tuple[ParsedTestResults | None, str | None]
        ] = OrderedDict()
        self.artifact_list_cache: OrderedDict[tuple[str, int], list[dict[str, Any]]] = OrderedDict()
        self.poll_attempts: dict[tuple[str, int], int] = {}

    def cache_run(self, key: tuple[str, int], result: ActionsRunResult) -> None:
        self.run_cache[key] = result
        self.run_cache.move_to_end(key)
        if len(self.run_cache) > self.max_entries:
            evicted, _ = self.run_cache.popitem(last=False)
            self.poll_attempts.pop(evicted, None)
        if self.is_terminal(result):
            self.poll_attempts.pop(key, None)

    def cache_artifact_result(
        self, key: tuple[str, int, int], parsed: ParsedTestResults | None, error: str | None
    ) -> None:
        self.artifact_cache[key] = (parsed, error)
        self.artifact_cache.move_to_end(key)
        if len(self.artifact_cache) > self.max_entries:
            self.artifact_cache.popitem(last=False)

    def cache_artifact_list(self, key: tuple[str, int], artifacts: list[dict[str, Any]]) -> None:
        self.artifact_list_cache[key] = artifacts
        self.artifact_list_cache.move_to_end(key)
        if len(self.artifact_list_cache) > self.max_entries:
            evicted, _ = self.artifact_list_cache.popitem(last=False)
            to_remove = [k for k in self.artifact_cache if k[0] == evicted[0] and k[1] == evicted[1]]
            for k in to_remove:
                self.artifact_cache.pop(k, None)

    @staticmethod
    def is_terminal(result: ActionsRunResult) -> bool:
        if result.conclusion:
            return True
        return result.status in {"passed", "failed", "cancelled", "timed_out", "error"}
