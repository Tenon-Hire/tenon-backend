from __future__ import annotations

import subprocess
from pathlib import Path

from app.trials.services import (
    trials_services_trials_codespace_specializer_runtime_service as runtime_service,
)


def test_rewrite_malformed_full_file_diff_repairs_missing_hunk_headers(
    tmp_path: Path,
) -> None:
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    target_file = repo_dir / "app.py"
    target_file.write_text(
        "from fastapi import FastAPI\n\napp = FastAPI()\n", encoding="utf-8"
    )

    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "add", "app.py"], cwd=repo_dir, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
        env={
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.com",
            "PATH": str(Path("/usr/bin")) + ":" + str(Path("/opt/homebrew/bin")),
        },
    )

    malformed = """diff --git a/app.py b/app.py
index 1111111..2222222 100644
--- a/app.py
+++ b/app.py
 from fastapi import FastAPI

+from fastapi.responses import JSONResponse
+
 app = FastAPI()
"""

    repaired = runtime_service._rewrite_malformed_full_file_diff(
        repo_dir=repo_dir,
        patch_text=malformed,
    )

    assert repaired is not None
    assert "@@" in repaired
    assert "JSONResponse" in repaired
