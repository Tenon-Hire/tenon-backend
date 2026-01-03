#!/usr/bin/env bash

set -e

echo "🚀 Tenon Backend — Local Runner"

PROJECT_ROOT="$(dirname "$0")"
cd "$PROJECT_ROOT" || exit 1

# Colors
GREEN='\033[0;32m'
NC='\033[0m'

if command -v poetry &> /dev/null
then
    echo -e "${GREEN}Using Poetry environment...${NC}"
    RUN="poetry run"
else
    echo -e "${GREEN}Poetry not found. Falling back to system Python/pip...${NC}"
    RUN=""
fi

if [[ "$1" == "test" ]]; then
    echo "🧪 Running tests..."
    $RUN pytest -q
    exit 0
fi

if [[ "$1" == "migrate" ]]; then
    echo "📦 Running Alembic migrations..."
    $RUN alembic upgrade head
    exit 0
fi

echo "🌱 Seeding local recruiters..."
export ENV=local
export DEV_AUTH_BYPASS=1
if [[ -f ./setEnvVar.sh ]]; then
    echo "🔧 Loading environment variables from setEnvVar.sh..."
else
    echo "⚠️  setEnvVar.sh not found."
    source ./setEnvVar.sh
fi

poetry run python scripts/seed_local_recruiters.py

echo "🔧 Starting FastAPI server..."

RELOAD_FLAG="--reload"
if [[ "${DISABLE_RELOAD:-0}" == "1" ]]; then
  RELOAD_FLAG=""
fi

$RUN uvicorn app.api.main:app ${RELOAD_FLAG} --host 0.0.0.0 --port 8000
