#!/usr/bin/env bash
set -euo pipefail

echo "🔍 Running pre-commit checks..."

# Directory of THIS script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# cd into backend dir (where pyproject.toml actually is)
cd "$SCRIPT_DIR"

POETRY_CMD="poetry"
if ! command -v "$POETRY_CMD" >/dev/null 2>&1; then
  echo "⚙️  Poetry not found. Installing..."
  install_status=0
  if command -v pipx >/dev/null 2>&1; then
    pipx install poetry || install_status=$?
    export PATH="$HOME/.local/bin:$PATH"
  elif command -v python3 >/dev/null 2>&1; then
    VENV_DIR="${SCRIPT_DIR}/.venv-poetry"
    python3 -m venv "$VENV_DIR" || install_status=$?
    if [[ $install_status -eq 0 ]]; then
      "$VENV_DIR/bin/pip" install poetry || install_status=$?
    fi
    POETRY_CMD="$VENV_DIR/bin/poetry"
  else
    install_status=1
  fi

  if [[ $install_status -ne 0 ]] || { ! command -v "$POETRY_CMD" >/dev/null 2>&1 && [[ ! -x "$POETRY_CMD" ]]; }; then
    echo "❌ Poetry install failed. Install manually and retry."
    exit 1
  fi
fi

echo "➡️  Linting backend with Ruff (autofix)..."
"$POETRY_CMD" run ruff check . --fix

echo "➡️  Formatting backend with Ruff..."
"$POETRY_CMD" run ruff format .

echo "➡️  Running backend tests..."
"$POETRY_CMD" run pytest --maxfail=1

echo "✅ All pre-commit checks passed!"
exit 0
