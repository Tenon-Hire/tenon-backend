#!/usr/bin/env bash
set -euo pipefail

echo "🔍 Running pre-commit checks..."

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

discover_poetry() {
  if [[ -n "${POETRY_BIN:-}" ]]; then
    if [[ "$POETRY_BIN" == */* ]]; then
      if [[ -x "$POETRY_BIN" ]]; then
        POETRY_CMD=("$POETRY_BIN")
        return 0
      fi
    elif command -v "$POETRY_BIN" >/dev/null 2>&1; then
      POETRY_CMD=("$(command -v "$POETRY_BIN")")
      return 0
    fi
  fi

  if command -v poetry >/dev/null 2>&1; then
    POETRY_CMD=("$(command -v poetry)")
    return 0
  fi

  local candidates=(
    "$HOME/.local/bin/poetry"
    "$HOME/Library/Python/3.12/bin/poetry"
    "$HOME/Library/Python/3.13/bin/poetry"
    "$HOME/Library/Python/3.14/bin/poetry"
    "/opt/homebrew/bin/poetry"
    "/usr/local/bin/poetry"
  )

  for candidate in "${candidates[@]}"; do
    if [[ -x "$candidate" ]]; then
      POETRY_CMD=("$candidate")
      return 0
    fi
  done

  echo "❌ Poetry not found." >&2
  echo "Install Poetry and rerun, or set POETRY_BIN to your Poetry executable path." >&2
  exit 1
}

poetry_run() {
  "${POETRY_CMD[@]}" run "$@"
}

POETRY_CMD=()
discover_poetry
echo "📦 Using Poetry: ${POETRY_CMD[*]}"

echo "🧹 Ruff lint..."
poetry_run ruff check . --fix

echo "➡️  Formatting backend with Ruff..."
poetry_run ruff format .

echo "🧪 Pytest..."
poetry_run pytest -v --maxfail=1

echo "✅ All pre-commit checks passed!"
exit 0
