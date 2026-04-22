from __future__ import annotations

import os
import subprocess
from pathlib import Path


def test_run_backend_bootstrap_local_sources_env_and_runs_seed_script(tmp_path):
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
                "WINOE_CUSTOM_MARKER=loaded",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    poetry_script = bin_dir / "poetry"
    poetry_script.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
echo "poetry:$*" >> "$TEST_COMMAND_LOG"
shift
if [[ "${1:-}" == "run" ]]; then
  shift
fi
exec "$@"
""",
        encoding="utf-8",
    )
    poetry_script.chmod(0o755)

    alembic_script = bin_dir / "alembic"
    alembic_script.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
{
  echo "alembic:$*"
  echo "marker:${WINOE_CUSTOM_MARKER:-missing}"
  echo "bypass:${DEV_AUTH_BYPASS:-missing}"
} >> "$TEST_COMMAND_LOG"
""",
        encoding="utf-8",
    )
    alembic_script.chmod(0o755)

    python_script = bin_dir / "python"
    python_script.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
{
  echo "python:$*"
  echo "marker:${WINOE_CUSTOM_MARKER:-missing}"
  echo "bypass:${DEV_AUTH_BYPASS:-missing}"
} >> "$TEST_COMMAND_LOG"
""",
        encoding="utf-8",
    )
    python_script.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["ENV_FILE"] = str(env_file)
    env["TEST_COMMAND_LOG"] = str(log_file)

    result = subprocess.run(
        ["bash", "runBackend.sh", "bootstrap-local"],
        cwd=repo_root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    log_output = log_file.read_text(encoding="utf-8")
    assert "poetry:run alembic upgrade head" in log_output
    assert "alembic:upgrade head" in log_output
    assert (
        "poetry:run python scripts/seed_local_talent_partners.py --reset"
        in log_output
    )
    assert "python:scripts/seed_local_talent_partners.py --reset" in log_output
    assert "marker:loaded" in log_output
    assert "bypass:0" in log_output
