from __future__ import annotations

import json
import subprocess
from types import SimpleNamespace

from app.ai import CodespacePatchProposal
from app.integrations.codespace_specializer.base_client import (
    CodespaceSpecializerProviderError,
    CodespaceSpecializerResponse,
)
from app.trials.services import (
    trials_services_trials_codespace_specializer_runtime_service as runtime_service,
)


def _scenario_version(test_command: str | None = "pytest -q") -> SimpleNamespace:
    return SimpleNamespace(
        id=4,
        template_key="python-fastapi",
        storyline_md="# Backend Engineer trial",
        codespace_spec_json={
            "summary": "Prepare the shared coding baseline.",
            "candidate_goal": "Fix the seeded FastAPI baseline.",
            "acceptance_criteria": ["Tests pass."],
            "target_files": ["README.md"],
            "test_command": test_command,
        },
        ai_policy_snapshot_json={
            "agents": {
                "codespace": {
                    "promptVersion": "v1:codespace",
                    "runtime": {
                        "runtimeMode": "real",
                        "provider": "openai",
                        "model": "gpt-5.4-mini",
                        "timeoutSeconds": 123,
                    },
                }
            }
        },
    )


def _trial() -> SimpleNamespace:
    return SimpleNamespace(
        id=10,
        title="Audit trial",
        role="Backend Engineer",
        tech_stack="Python, FastAPI, pytest",
        focus="Validate the live workflow.",
        company_context={"domain": "B2B tooling"},
    )


class _FakeProvider:
    def specialize_codespace(self, *, request):
        return CodespaceSpecializerResponse(
            result=CodespacePatchProposal(
                plan_md="Apply a narrow patch.",
                commit_message="feat: seed candidate baseline",
                unified_diff="diff --git a/README.md b/README.md\n",
            ),
            model_name=request.model,
            model_version=request.model,
        )


async def _noop_async(*_args, **_kwargs) -> None:
    return None


async def test_generate_codespace_bundle_artifact_uses_snapshot_prompt_version_and_runtime_timeout(
    monkeypatch,
) -> None:
    observed: dict[str, object] = {}

    async def _git_head_sha(*_args, **_kwargs):
        return "abc123"

    async def _build_repo_snapshot(*_args, **_kwargs):
        return {"files": []}

    async def _apply_unified_diff(*_args, **_kwargs):
        return runtime_service.CommandResult(exit_code=0, stdout="", stderr="")

    async def _run_shell_command(*, command: str, cwd, timeout_seconds: int):
        observed["command"] = command
        observed["timeout_seconds"] = timeout_seconds
        observed["cwd"] = str(cwd)
        return runtime_service.CommandResult(exit_code=0, stdout="ok", stderr="")

    async def _build_patch_payload_json(*_args, **_kwargs):
        return '{"files":[{"path":"README.md","content":"patched","executable":false}]}'

    monkeypatch.setattr(runtime_service, "_clone_repo", _noop_async)
    monkeypatch.setattr(runtime_service, "_git_head_sha", _git_head_sha)
    monkeypatch.setattr(runtime_service, "_build_repo_snapshot", _build_repo_snapshot)
    monkeypatch.setattr(
        runtime_service,
        "build_required_snapshot_prompt",
        lambda **_kwargs: ("system", "rubric"),
    )
    monkeypatch.setattr(
        runtime_service,
        "get_codespace_specializer_provider",
        lambda _provider: _FakeProvider(),
    )
    monkeypatch.setattr(runtime_service, "_reset_repo", _noop_async)
    monkeypatch.setattr(runtime_service, "_apply_unified_diff", _apply_unified_diff)
    monkeypatch.setattr(runtime_service, "_run_shell_command", _run_shell_command)
    monkeypatch.setattr(
        runtime_service, "_build_patch_payload_json", _build_patch_payload_json
    )

    artifact = await runtime_service.generate_codespace_bundle_artifact(
        template_repo_full_name="acme/python-fastapi-template",
        scenario_version=_scenario_version(),
        trial=_trial(),
    )

    assert observed["command"] == "pytest -q"
    assert observed["timeout_seconds"] == 123
    assert artifact.prompt_version == "v1:codespace"
    assert artifact.model_name == "gpt-5.4-mini"


async def test_generate_codespace_bundle_artifact_second_attempt_uses_failed_repo_snapshot(
    monkeypatch,
) -> None:
    observed_prompts: list[dict[str, object]] = []
    snapshot_calls: list[list[str] | None] = []

    class _RecordingProvider:
        def specialize_codespace(self, *, request):
            observed_prompts.append(json.loads(request.user_prompt))
            return CodespaceSpecializerResponse(
                result=CodespacePatchProposal(
                    plan_md="Apply a narrow patch.",
                    commit_message="feat: seed candidate baseline",
                    unified_diff="diff --git a/README.md b/README.md\n",
                ),
                model_name=request.model,
                model_version=request.model,
            )

    async def _git_head_sha(*_args, **_kwargs):
        return "abc123"

    async def _build_repo_snapshot(*_args, priority_paths=None, **_kwargs):
        snapshot_calls.append(priority_paths)
        if len(snapshot_calls) == 1:
            return {
                "trackedPaths": ["README.md"],
                "untrackedPaths": [],
                "files": [{"path": "README.md", "content": "base snapshot"}],
                "truncated": False,
            }
        return {
            "trackedPaths": ["README.md"],
            "untrackedPaths": ["tests/test_workflow_patch.py"],
            "files": [
                {
                    "path": "tests/test_workflow_patch.py",
                    "content": "with pytest.raises(HTTPException): ...",
                }
            ],
            "truncated": False,
        }

    shell_call_count = 0

    async def _run_shell_command(*, command: str, cwd, timeout_seconds: int):
        nonlocal shell_call_count
        shell_call_count += 1
        if shell_call_count == 1:
            return runtime_service.CommandResult(
                exit_code=1,
                stdout=(
                    "FAILED tests/test_workflow_patch.py::"
                    "test_patch_service_rejects_malformed_steps"
                ),
                stderr="",
            )
        return runtime_service.CommandResult(
            exit_code=0,
            stdout="ok",
            stderr="",
        )

    async def _apply_unified_diff(*_args, **_kwargs):
        return runtime_service.CommandResult(exit_code=0, stdout="", stderr="")

    async def _build_patch_payload_json(*_args, **_kwargs):
        return '{"files":[{"path":"README.md","content":"patched","executable":false}]}'

    async def _list_changed_paths(*_args, **_kwargs):
        return ["tests/test_workflow_patch.py"]

    monkeypatch.setattr(runtime_service, "_clone_repo", _noop_async)
    monkeypatch.setattr(runtime_service, "_git_head_sha", _git_head_sha)
    monkeypatch.setattr(runtime_service, "_build_repo_snapshot", _build_repo_snapshot)
    monkeypatch.setattr(
        runtime_service,
        "build_required_snapshot_prompt",
        lambda **_kwargs: ("system", "rubric"),
    )
    monkeypatch.setattr(
        runtime_service,
        "get_codespace_specializer_provider",
        lambda _provider: _RecordingProvider(),
    )
    monkeypatch.setattr(runtime_service, "_reset_repo", _noop_async)
    monkeypatch.setattr(runtime_service, "_apply_unified_diff", _apply_unified_diff)
    monkeypatch.setattr(runtime_service, "_run_shell_command", _run_shell_command)
    monkeypatch.setattr(
        runtime_service, "_build_patch_payload_json", _build_patch_payload_json
    )
    monkeypatch.setattr(runtime_service, "_list_changed_paths", _list_changed_paths)

    artifact = await runtime_service.generate_codespace_bundle_artifact(
        template_repo_full_name="acme/python-fastapi-template",
        scenario_version=_scenario_version(),
        trial=_trial(),
    )

    assert artifact.test_summary_json["status"] == "passed"
    assert len(observed_prompts) == 2
    assert snapshot_calls == [None, ["tests/test_workflow_patch.py"]]

    second_prompt = observed_prompts[1]
    repair_context = second_prompt["repairContext"]
    assert second_prompt["attempt"] == 2
    assert repair_context["failureType"] == "test_failure"
    assert "FAILED tests/test_workflow_patch.py" in repair_context["stdout"]
    assert repair_context["previousUnifiedDiff"] == "diff --git a/README.md b/README.md"
    assert second_prompt["baseRepositorySnapshot"]["files"][0]["path"] == "README.md"
    assert (
        second_prompt["repairRepositorySnapshot"]["files"][0]["path"]
        == "tests/test_workflow_patch.py"
    )
    assert second_prompt["repositorySnapshot"]["files"][0]["path"] == (
        "tests/test_workflow_patch.py"
    )


def test_is_retryable_codespace_specializer_error_detects_provider_throttling() -> None:
    assert runtime_service.is_retryable_codespace_specializer_error(
        CodespaceSpecializerProviderError("openai_request_failed:RateLimitError")
    )
    assert not runtime_service.is_retryable_codespace_specializer_error(
        CodespaceSpecializerProviderError("codespace_patch_apply_failed")
    )


def test_build_retryable_provider_fallback_bundle_artifact_records_reason() -> None:
    artifact = runtime_service.build_retryable_provider_fallback_bundle_artifact(
        scenario_version=_scenario_version(),
        template_repo_full_name="acme/python-fastapi-template",
        fallback_reason="openai_request_failed:RateLimitError",
    )

    payload = json.loads(artifact.patch_payload_json)

    assert artifact.model_name == "deterministic-provider-fallback"
    assert artifact.test_summary_json["attempts"][0]["reason"] == (
        "provider_retryable_fallback"
    )
    assert artifact.provenance_json["mode"] == "provider_retryable_fallback"
    assert (
        artifact.provenance_json["fallbackReason"]
        == "openai_request_failed:RateLimitError"
    )
    assert payload["files"][0]["path"] == "WINOE_TRIAL_CONTEXT.md"


def test_resolve_test_command_prefixes_pythonpath_for_pytest_repos(tmp_path) -> None:
    (tmp_path / "app").mkdir()
    spec = runtime_service.CodespaceSpec(
        summary="Prepare baseline.",
        candidate_goal="Ship a candidate-ready repo.",
        acceptance_criteria=["Tests pass."],
        test_command="pytest -q",
    )

    assert (
        runtime_service._resolve_test_command(tmp_path, spec)
        == "PYTHONPATH=. pytest -q"
    )


async def test_build_repo_snapshot_includes_untracked_priority_files(tmp_path) -> None:
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    def _git(*args: str) -> None:
        subprocess.run(
            ["git", *args],
            cwd=repo_dir,
            check=True,
            capture_output=True,
            text=True,
        )

    _git("init", "-q")
    (repo_dir / "README.md").write_text("# Template\n", encoding="utf-8")
    _git("add", "README.md")
    _git(
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-qm",
        "init",
    )
    (repo_dir / "tests").mkdir()
    (repo_dir / "tests" / "test_workflow_patch.py").write_text(
        "def test_generated():\n    assert True\n",
        encoding="utf-8",
    )

    snapshot = await runtime_service._build_repo_snapshot(
        repo_dir,
        runtime_service.CodespaceSpec(
            summary="Prepare baseline.",
            candidate_goal="Ship a candidate-ready repo.",
            acceptance_criteria=["Tests pass."],
            target_files=[],
        ),
        priority_paths=["tests/test_workflow_patch.py"],
    )

    assert snapshot["untrackedPaths"] == ["tests/test_workflow_patch.py"]
    assert snapshot["files"][0]["path"] == "tests/test_workflow_patch.py"


async def test_build_repo_snapshot_prioritizes_glob_target_files_before_truncation(
    tmp_path,
    monkeypatch,
) -> None:
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    def _git(*args: str) -> None:
        subprocess.run(
            ["git", *args],
            cwd=repo_dir,
            check=True,
            capture_output=True,
            text=True,
        )

    _git("init", "-q")
    (repo_dir / "README.md").write_text("# Template\n", encoding="utf-8")
    (repo_dir / "app").mkdir()
    (repo_dir / "tests").mkdir()
    for index in range(1, 4):
        (repo_dir / "app" / f"module_{index}.py").write_text(
            ("VALUE = 1\n" * 40),
            encoding="utf-8",
        )
    (repo_dir / "tests" / "conftest.py").write_text(
        "from fastapi.testclient import TestClient\n",
        encoding="utf-8",
    )
    (repo_dir / "tests" / "test_api.py").write_text(
        "def test_api():\n    assert True\n",
        encoding="utf-8",
    )
    (repo_dir / "tests" / "test_service.py").write_text(
        "def test_service():\n    assert True\n",
        encoding="utf-8",
    )
    _git("add", ".")
    _git(
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-qm",
        "init",
    )

    monkeypatch.setattr(runtime_service, "_MAX_SNAPSHOT_FILES", 3)
    monkeypatch.setattr(runtime_service, "_MAX_SNAPSHOT_CHARS", 200)
    monkeypatch.setattr(runtime_service, "_MAX_FILE_SNAPSHOT_CHARS", 200)

    snapshot = await runtime_service._build_repo_snapshot(
        repo_dir,
        runtime_service.CodespaceSpec(
            summary="Prepare baseline.",
            candidate_goal="Ship a candidate-ready repo.",
            acceptance_criteria=["Tests pass."],
            target_files=["tests/test_*.py"],
        ),
    )

    included_paths = [item["path"] for item in snapshot["files"]]
    assert "tests/test_api.py" in included_paths
    assert "tests/test_service.py" in included_paths


async def test_apply_unified_diff_repairs_bad_hunk_counts(tmp_path) -> None:
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    def _git(*args: str) -> None:
        subprocess.run(
            ["git", *args],
            cwd=repo_dir,
            check=True,
            capture_output=True,
            text=True,
        )

    _git("init", "-q")
    (repo_dir / "README.md").write_text("alpha\nbeta\n", encoding="utf-8")
    _git("add", "README.md")
    _git(
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-qm",
        "init",
    )

    malformed_patch = """\
diff --git a/README.md b/README.md
index 1111111..2222222 100644
--- a/README.md
+++ b/README.md
@@ -1,9 +1,11 @@
 alpha
+bravo
 beta
diff --git a/NOTES.md b/NOTES.md
new file mode 100644
index 0000000..3333333
--- /dev/null
+++ b/NOTES.md
@@ -0,0 +1,5 @@
+one
+two
"""

    result = await runtime_service._apply_unified_diff(
        repo_dir=repo_dir,
        unified_diff=malformed_patch,
    )

    assert result.exit_code == 0
    assert (repo_dir / "README.md").read_text(
        encoding="utf-8"
    ) == "alpha\nbravo\nbeta\n"
    assert (repo_dir / "NOTES.md").read_text(encoding="utf-8") == "one\ntwo\n"


async def test_apply_unified_diff_normalizes_existing_file_marked_as_new(
    tmp_path,
) -> None:
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    def _git(*args: str) -> None:
        subprocess.run(
            ["git", *args],
            cwd=repo_dir,
            check=True,
            capture_output=True,
            text=True,
        )

    _git("init", "-q")
    (repo_dir / "tests").mkdir()
    (repo_dir / "tests" / "test_api.py").write_text(
        "def test_health():\n    assert True\n",
        encoding="utf-8",
    )
    _git("add", "tests/test_api.py")
    _git(
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-qm",
        "init",
    )

    malformed_patch = """\
diff --git a/tests/test_api.py b/tests/test_api.py
new file mode 100644
index 0000000..3333333
--- /dev/null
+++ b/tests/test_api.py
@@ -0,0 +1,5 @@
+def test_health():
+    assert True
+
+def test_ready():
+    assert True
"""

    result = await runtime_service._apply_unified_diff(
        repo_dir=repo_dir,
        unified_diff=malformed_patch,
    )

    assert result.exit_code == 0
    assert (repo_dir / "tests" / "test_api.py").read_text(encoding="utf-8") == (
        "def test_health():\n"
        "    assert True\n"
        "\n"
        "def test_ready():\n"
        "    assert True\n"
    )


async def test_apply_unified_diff_rewrites_deleted_file_block_with_missing_delete_prefix(
    tmp_path,
) -> None:
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    def _git(*args: str) -> None:
        subprocess.run(
            ["git", *args],
            cwd=repo_dir,
            check=True,
            capture_output=True,
            text=True,
        )

    _git("init", "-q")
    (repo_dir / "app" / "api" / "routes").mkdir(parents=True)
    target_path = repo_dir / "app" / "api" / "routes" / "items.py"
    target_path.write_text(
        "from __future__ import annotations\n"
        "\n"
        "def get_item_service() -> int:\n"
        "    return 1\n",
        encoding="utf-8",
    )
    _git("add", "app/api/routes/items.py")
    _git(
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-qm",
        "init",
    )

    malformed_patch = """\
diff --git a/app/api/routes/items.py b/app/api/routes/items.py
deleted file mode 100644
index 1111111..0000000 100644
--- a/app/api/routes/items.py
+++ /dev/null
@@ -1,4 +0,0 @@
-from __future__ import annotations
-
def get_item_service() -> int:
-    return 1
"""

    result = await runtime_service._apply_unified_diff(
        repo_dir=repo_dir,
        unified_diff=malformed_patch,
    )

    assert result.exit_code == 0
    assert not target_path.exists()


async def test_apply_unified_diff_rewrites_added_file_block_with_missing_add_prefix(
    tmp_path,
) -> None:
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    def _git(*args: str) -> None:
        subprocess.run(
            ["git", *args],
            cwd=repo_dir,
            check=True,
            capture_output=True,
            text=True,
        )

    _git("init", "-q")
    (repo_dir / "README.md").write_text("# Template\n", encoding="utf-8")
    _git("add", "README.md")
    _git(
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-qm",
        "init",
    )

    malformed_patch = """\
diff --git a/app/api/routes/shipments.py b/app/api/routes/shipments.py
new file mode 100644
index 0000000..3333333 100644
--- /dev/null
+++ b/app/api/routes/shipments.py
@@ -0,0 +1,4 @@
+from fastapi import APIRouter
+
router = APIRouter()
+__all__ = ["router"]
"""

    result = await runtime_service._apply_unified_diff(
        repo_dir=repo_dir,
        unified_diff=malformed_patch,
    )

    assert result.exit_code == 0
    assert (repo_dir / "app" / "api" / "routes" / "shipments.py").read_text(
        encoding="utf-8"
    ) == (
        "from fastapi import APIRouter\n"
        "\n"
        "router = APIRouter()\n"
        '__all__ = ["router"]\n'
    )


async def test_apply_unified_diff_rewrites_single_hunk_full_file_block_when_context_misses(
    tmp_path,
) -> None:
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    def _git(*args: str) -> None:
        subprocess.run(
            ["git", *args],
            cwd=repo_dir,
            check=True,
            capture_output=True,
            text=True,
        )

    _git("init", "-q")
    target_path = repo_dir / "README.md"
    target_path.write_text(
        "# Winoe Template\n" "Original intro\n" "Line A\n" "Line B\n",
        encoding="utf-8",
    )
    _git("add", "README.md")
    _git(
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-qm",
        "init",
    )

    malformed_patch = """\
diff --git a/README.md b/README.md
index 1111111..2222222 100644
--- a/README.md
+++ b/README.md
@@ -1,4 +1,4 @@
-# Different Template
+# Proofline Live Proof Workspace
-
-Starter intro
+FastAPI + pytest starter for the live proof repair.
 Line A
-Line B
+Line C
"""

    result = await runtime_service._apply_unified_diff(
        repo_dir=repo_dir,
        unified_diff=malformed_patch,
    )

    assert result.exit_code == 0
    assert target_path.read_text(encoding="utf-8") == (
        "# Proofline Live Proof Workspace\n"
        "FastAPI + pytest starter for the live proof repair.\n"
        "Line A\n"
        "Line C\n"
    )


async def test_apply_unified_diff_accepts_codex_add_delete_patch_blocks(
    tmp_path,
) -> None:
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    def _git(*args: str) -> None:
        subprocess.run(
            ["git", *args],
            cwd=repo_dir,
            check=True,
            capture_output=True,
            text=True,
        )

    _git("init", "-q")
    (repo_dir / "README.md").write_text("alpha\n", encoding="utf-8")
    _git("add", "README.md")
    _git(
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-qm",
        "init",
    )

    codex_patch = """\
*** Begin Patch
*** Delete File: README.md
*** End Patch
*** Begin Patch
*** Add File: README.md
+beta
+gamma
*** End Patch
*** Begin Patch
*** Add File: NOTES.md
+one
two
*** End Patch
"""

    result = await runtime_service._apply_unified_diff(
        repo_dir=repo_dir,
        unified_diff=codex_patch,
    )

    assert result.exit_code == 0
    assert (repo_dir / "README.md").read_text(encoding="utf-8") == "beta\ngamma\n"
    assert (repo_dir / "NOTES.md").read_text(encoding="utf-8") == "one\ntwo\n"


async def test_apply_unified_diff_accepts_codex_update_file_patch_blocks(
    tmp_path,
) -> None:
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    def _git(*args: str) -> None:
        subprocess.run(
            ["git", *args],
            cwd=repo_dir,
            check=True,
            capture_output=True,
            text=True,
        )

    _git("init", "-q")
    (repo_dir / "app").mkdir()
    (repo_dir / "app" / "main.py").write_text(
        "from fastapi import FastAPI\n\napp = FastAPI()\n",
        encoding="utf-8",
    )
    _git("add", "app/main.py")
    _git(
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-qm",
        "init",
    )

    codex_patch = """\
*** Begin Patch
*** Update File: app/main.py
@@
 from fastapi import FastAPI

 app = FastAPI()
+app.title = "Winoe"
*** End Patch
"""

    result = await runtime_service._apply_unified_diff(
        repo_dir=repo_dir,
        unified_diff=codex_patch,
    )

    assert result.exit_code == 0
    assert (repo_dir / "app" / "main.py").read_text(encoding="utf-8") == (
        "from fastapi import FastAPI\n" "\n" "app = FastAPI()\n" 'app.title = "Winoe"\n'
    )


async def test_rewrite_patch_as_full_file_diffs_preserves_untouched_lines(
    tmp_path,
) -> None:
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    def _git(*args: str) -> None:
        subprocess.run(
            ["git", *args],
            cwd=repo_dir,
            check=True,
            capture_output=True,
            text=True,
        )

    _git("init", "-q")
    (repo_dir / "app").mkdir()
    (repo_dir / "tests").mkdir()
    (repo_dir / "app" / "sample.py").write_text(
        "from __future__ import annotations\n"
        "\n"
        "import alpha\n"
        "import beta\n"
        "\n"
        "VALUE = 1\n"
        "OTHER = 2\n"
        "\n"
        "FOOTER = 'done'\n",
        encoding="utf-8",
    )
    (repo_dir / "tests" / "test_api.py").write_text(
        "def test_existing():\n    assert True\n",
        encoding="utf-8",
    )
    _git("add", "app/sample.py", "tests/test_api.py")
    _git(
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-qm",
        "init",
    )

    malformed_patch = """\
diff --git a/app/sample.py b/app/sample.py
index 1111111..2222222 100644
--- a/app/sample.py
+++ b/app/sample.py
@@ -3,3 +3,3 @@
 import alpha
-import beta
+import gamma

@@ -9,1 +9,1 @@
-FOOTER = 'done'
+FOOTER = 'ready'
diff --git a/tests/test_api.py b/tests/test_api.py
new file mode 100644
index 0000000..3333333 100644
--- /dev/null
+++ b/tests/test_api.py
@@ -0,0 +1,3 @@
+def test_existing():
+    assert True
+def test_added():
+    assert True
"""

    rewritten = runtime_service._rewrite_patch_as_full_file_diffs(
        repo_dir=repo_dir,
        patch_text=malformed_patch,
    )

    assert rewritten is not None
    patch_path = repo_dir / "rewritten.patch"
    patch_path.write_text(rewritten, encoding="utf-8")
    subprocess.run(
        ["git", "apply", str(patch_path)],
        cwd=repo_dir,
        check=True,
        capture_output=True,
        text=True,
    )
    assert (repo_dir / "app" / "sample.py").read_text(encoding="utf-8") == (
        "from __future__ import annotations\n"
        "\n"
        "import alpha\n"
        "import gamma\n"
        "\n"
        "VALUE = 1\n"
        "OTHER = 2\n"
        "\n"
        "FOOTER = 'ready'\n"
    )
