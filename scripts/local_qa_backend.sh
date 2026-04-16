#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Load the configured runtime once, then pin the supported local QA overrides.
# runBackend.sh sources ENV_FILE again, so redirect it to /dev/null after loading
# to keep the committed bypass flags from being reset by .env defaults.
if [[ -f ./setEnvVar.sh ]]; then
  # shellcheck disable=SC1091
  source ./setEnvVar.sh >/dev/null
fi

export WINOE_ENV=local
export DEV_AUTH_BYPASS=1
export WINOE_DEV_AUTH_BYPASS=1
export ENV_FILE=/dev/null

exec bash ./runBackend.sh "${1:-up}" "${@:2}"
