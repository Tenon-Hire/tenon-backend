from __future__ import annotations

from tests.shared.utils.shared_coverage_gaps_utils import *


def test_legacy_cache_and_results_mixins():
    class Holder(LegacyCacheMixin, LegacyResultMixin):
        pass

    cache = SimpleNamespace(
        run_cache={},
        artifact_cache={},
        artifact_list_cache={},
        poll_attempts={},
        max_entries=5,
        cache_run=lambda key, val: cache.run_cache.__setitem__(key, val),
        cache_artifact_result=lambda key,
        parsed,
        error: cache.artifact_cache.__setitem__(key, (parsed, error)),
        cache_artifact_list=lambda key,
        artifacts: cache.artifact_list_cache.__setitem__(key, artifacts),
    )
    holder = Holder()
    holder.cache = cache
    holder._cache_run_result(("repo", 1), "value")
    assert holder._run_cache[("repo", 1)] == "value"
    holder._cache_artifact_result("k", {"ok": True}, None)
    assert holder._artifact_cache["k"][0]["ok"] is True
    holder._cache_artifact_list("k", [1])
    assert holder._artifact_list_cache["k"] == [1]
    _ = holder._poll_attempts
    holder._max_cache_entries = 99
    assert holder._max_cache_entries == 99
    assert holder._run_cache_key("owner/repo", 55) == ("owner/repo", 55)
