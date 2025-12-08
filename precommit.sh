#!/usr/bin/env bash
set -euo pipefail

echo "🔍 Running pre-commit checks..."


if [ -d "backend" ]; then
  echo "➡️  Linting backend with Ruff..."
  poetry run ruff check backend

  echo "➡️  Formatting backend with Ruff..."
  poetry run ruff format backend

  echo "➡️  Running backend tests..."
  poetry run pytest --maxfail=1
fi


echo "✅ All pre-commit checks passed!"
exit 0
