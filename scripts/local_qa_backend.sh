#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Load the configured runtime once, then pin the supported local QA overrides.
# runBackend.sh sources ENV_FILE again, so keep the configured env file in place
# and override the bypass flags explicitly after loading.
if [[ -f ./setEnvVar.sh ]]; then
  # shellcheck disable=SC1091
  source ./setEnvVar.sh >/dev/null
fi

export WINOE_ENV=local
export DEV_AUTH_BYPASS=1
export WINOE_DEV_AUTH_BYPASS=1
export WINOE_SCENARIO_GENERATION_RUNTIME_MODE=real

exec bash ./runBackend.sh "${1:-up}" "${@:2}"
