from __future__ import annotations

import os
import subprocess
from pathlib import Path


def test_local_qa_backend_exports_supported_local_bypass(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    log_file = tmp_path / "command.log"

    fake_bash = bin_dir / "bash"
    fake_bash.write_text(
        """#!/bin/bash
set -euo pipefail
{
  echo "argv:$*"
  echo "env_file:${ENV_FILE:-missing}"
  echo "winoe_env:${WINOE_ENV:-missing}"
  echo "dev_auth_bypass:${DEV_AUTH_BYPASS:-missing}"
  echo "winoe_dev_auth_bypass:${WINOE_DEV_AUTH_BYPASS:-missing}"
  echo "scenario_generation_runtime_mode:${WINOE_SCENARIO_GENERATION_RUNTIME_MODE:-missing}"
} >> "$TEST_COMMAND_LOG"
""",
        encoding="utf-8",
    )
    fake_bash.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["TEST_COMMAND_LOG"] = str(log_file)
    env["ENV_FILE"] = str(tmp_path / "qa.env")
    (tmp_path / "qa.env").write_text(
        "DEV_AUTH_BYPASS=0\nWINOE_DEV_AUTH_BYPASS=0\n", encoding="utf-8"
    )

    result = subprocess.run(
        ["/bin/bash", "scripts/local_qa_backend.sh", "api"],
        cwd=repo_root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    log_output = log_file.read_text(encoding="utf-8")
    assert "argv:./runBackend.sh api" in log_output
    assert f"env_file:{env['ENV_FILE']}" in log_output
    assert "winoe_env:local" in log_output
    assert "dev_auth_bypass:1" in log_output
    assert "winoe_dev_auth_bypass:1" in log_output
    assert "scenario_generation_runtime_mode:real" in log_output
