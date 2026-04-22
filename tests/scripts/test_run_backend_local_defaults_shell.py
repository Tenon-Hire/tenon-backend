from __future__ import annotations

import os
import subprocess
from pathlib import Path


def test_run_backend_api_exports_local_real_scenario_generation_defaults(
    tmp_path,
):
    repo_root = Path(__file__).resolve().parents[2]
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    log_file = tmp_path / "command.log"
    env_file = tmp_path / "runtime.env"
    env_file.write_text(
        "\n".join(
            [
                "WINOE_DATABASE_URL=sqlite:///tmp/winoe.db",
                "WINOE_DATABASE_URL_SYNC=sqlite:///tmp/winoe.db",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    poetry_script = bin_dir / "poetry"
    poetry_script.write_text(
        """#!/bin/bash
set -euo pipefail
{
  echo "poetry:$*"
  echo "scenario_generation_runtime_mode:${WINOE_SCENARIO_GENERATION_RUNTIME_MODE:-missing}"
  echo "scenario_generation_provider:${WINOE_SCENARIO_GENERATION_PROVIDER:-missing}"
  echo "scenario_generation_model:${WINOE_SCENARIO_GENERATION_MODEL:-missing}"
  echo "dev_auth_bypass:${DEV_AUTH_BYPASS:-missing}"
  echo "winoe_env:${WINOE_ENV:-missing}"
} >> "$TEST_COMMAND_LOG"
shift
if [[ "${1:-}" == "run" ]]; then
  shift
fi
exec "$@"
""",
        encoding="utf-8",
    )
    poetry_script.chmod(0o755)

    uvicorn_script = bin_dir / "uvicorn"
    uvicorn_script.write_text(
        """#!/bin/bash
set -euo pipefail
{
  echo "uvicorn:$*"
  echo "scenario_generation_runtime_mode:${WINOE_SCENARIO_GENERATION_RUNTIME_MODE:-missing}"
  echo "scenario_generation_provider:${WINOE_SCENARIO_GENERATION_PROVIDER:-missing}"
  echo "scenario_generation_model:${WINOE_SCENARIO_GENERATION_MODEL:-missing}"
  echo "dev_auth_bypass:${DEV_AUTH_BYPASS:-missing}"
  echo "winoe_env:${WINOE_ENV:-missing}"
} >> "$TEST_COMMAND_LOG"
""",
        encoding="utf-8",
    )
    uvicorn_script.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["ENV_FILE"] = str(env_file)
    env["TEST_COMMAND_LOG"] = str(log_file)
    env["WINOE_ENV"] = "local"

    result = subprocess.run(
        ["bash", "runBackend.sh", "api"],
        cwd=repo_root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    log_output = log_file.read_text(encoding="utf-8")
    assert (
        "poetry:run uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000"
        in log_output
    )
    assert "uvicorn:app.api.main:app --reload --host 0.0.0.0 --port 8000" in log_output
    assert "scenario_generation_runtime_mode:real" in log_output
    assert "scenario_generation_provider:anthropic" in log_output
    assert "scenario_generation_model:claude-opus-4-6" in log_output
    assert "winoe_env:local" in log_output


def test_run_backend_api_preserves_explicit_scenario_generation_env_values(
    tmp_path,
):
    repo_root = Path(__file__).resolve().parents[2]
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    log_file = tmp_path / "command.log"
    env_file = tmp_path / "runtime.env"
    env_file.write_text(
        "\n".join(
            [
                "WINOE_DATABASE_URL=sqlite:///tmp/winoe.db",
                "WINOE_DATABASE_URL_SYNC=sqlite:///tmp/winoe.db",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    poetry_script = bin_dir / "poetry"
    poetry_script.write_text(
        """#!/bin/bash
set -euo pipefail
{
  echo "poetry:$*"
  echo "scenario_generation_runtime_mode:${WINOE_SCENARIO_GENERATION_RUNTIME_MODE:-missing}"
  echo "scenario_generation_provider:${WINOE_SCENARIO_GENERATION_PROVIDER:-missing}"
  echo "scenario_generation_model:${WINOE_SCENARIO_GENERATION_MODEL:-missing}"
  echo "dev_auth_bypass:${DEV_AUTH_BYPASS:-missing}"
  echo "winoe_env:${WINOE_ENV:-missing}"
} >> "$TEST_COMMAND_LOG"
shift
if [[ "${1:-}" == "run" ]]; then
  shift
fi
exec "$@"
""",
        encoding="utf-8",
    )
    poetry_script.chmod(0o755)

    uvicorn_script = bin_dir / "uvicorn"
    uvicorn_script.write_text(
        """#!/bin/bash
set -euo pipefail
{
  echo "uvicorn:$*"
  echo "scenario_generation_runtime_mode:${WINOE_SCENARIO_GENERATION_RUNTIME_MODE:-missing}"
  echo "scenario_generation_provider:${WINOE_SCENARIO_GENERATION_PROVIDER:-missing}"
  echo "scenario_generation_model:${WINOE_SCENARIO_GENERATION_MODEL:-missing}"
  echo "dev_auth_bypass:${DEV_AUTH_BYPASS:-missing}"
  echo "winoe_env:${WINOE_ENV:-missing}"
} >> "$TEST_COMMAND_LOG"
""",
        encoding="utf-8",
    )
    uvicorn_script.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["ENV_FILE"] = str(env_file)
    env["TEST_COMMAND_LOG"] = str(log_file)
    env["WINOE_ENV"] = "local"
    env["WINOE_SCENARIO_GENERATION_RUNTIME_MODE"] = "demo"
    env["WINOE_SCENARIO_GENERATION_PROVIDER"] = "anthropic"
    env["WINOE_SCENARIO_GENERATION_MODEL"] = "claude-opus-4-6"

    result = subprocess.run(
        ["bash", "runBackend.sh", "api"],
        cwd=repo_root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    log_output = log_file.read_text(encoding="utf-8")
    assert "scenario_generation_runtime_mode:demo" in log_output
    assert "scenario_generation_provider:anthropic" in log_output
    assert "scenario_generation_model:claude-opus-4-6" in log_output
    assert "winoe_env:local" in log_output
