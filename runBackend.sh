#!/usr/bin/env bash

set -e

echo "🚀 Winoe Backend — Local Runner"

PROJECT_ROOT="$(dirname "$0")"
cd "$PROJECT_ROOT" || exit 1

# Colors
GREEN='\033[0;32m'
NC='\033[0m'

POETRY_CMD="poetry"
USE_POETRY=0

if command -v "$POETRY_CMD" &> /dev/null; then
    USE_POETRY=1
else
    echo -e "${GREEN}Poetry not found. Installing...${NC}"
    install_status=0
    if command -v pipx &> /dev/null; then
        pipx install poetry || install_status=$?
        export PATH="$HOME/.local/bin:$PATH"
    elif command -v python3 &> /dev/null; then
        VENV_DIR="${PROJECT_ROOT}/.venv-poetry"
        python3 -m venv "$VENV_DIR" || install_status=$?
        if [[ $install_status -eq 0 ]]; then
            "$VENV_DIR/bin/pip" install poetry || install_status=$?
        fi
        POETRY_CMD="$VENV_DIR/bin/poetry"
    else
        install_status=1
    fi

    if [[ $install_status -eq 0 ]] && { command -v "$POETRY_CMD" &> /dev/null || [[ -x "$POETRY_CMD" ]]; }; then
        USE_POETRY=1
    else
        if [[ -x "${PROJECT_ROOT}/.venv/bin/python" ]]; then
            echo -e "${GREEN}Poetry install failed. Using existing .venv...${NC}"
            export PATH="${PROJECT_ROOT}/.venv/bin:$PATH"
        else
            echo "ERROR: Poetry install failed and no .venv found."
            exit 1
        fi
    fi
fi

if [[ $USE_POETRY -eq 1 ]]; then
    echo -e "${GREEN}Using Poetry environment...${NC}"
    RUN="$POETRY_CMD run"
else
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

echo "🌱 Seeding local talent_partners..."
export ENV=local
export DEV_AUTH_BYPASS=1
source ./setEnvVar.sh

$RUN python scripts/seed_local_talent_partners.py

echo "🔧 Starting FastAPI server..."

RELOAD_FLAG="--reload"
if [[ "${DISABLE_RELOAD:-0}" == "1" ]]; then
  RELOAD_FLAG=""
fi

$RUN uvicorn app.api.main:app ${RELOAD_FLAG} --host 0.0.0.0 --port 8000
