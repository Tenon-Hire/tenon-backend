#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

POETRY_CMD="poetry"
USE_POETRY=0
RUN_PREFIX=()

log_info() {
  printf '%s\n' "$*"
}

log_error() {
  printf '%s\n' "$*" >&2
}

load_environment() {
  if [[ -n "${ENV_FILE:-}" && -f "${ENV_FILE}" ]]; then
    # Load the explicitly provided env file first so test harnesses and local
    # callers can override shell defaults deterministically.
    # shellcheck disable=SC1090
    set -a
    source "${ENV_FILE}"
    set +a
  fi

  if [[ -f ./setEnvVar.sh ]]; then
    source ./setEnvVar.sh
  fi
}

apply_local_defaults() {
  if [[ -z "${WINOE_ENV:-}" || "${WINOE_ENV:-}" == "local" ]]; then
    export WINOE_ENV="${WINOE_ENV:-local}"
    export DEV_AUTH_BYPASS="${DEV_AUTH_BYPASS:-1}"
    # Local runs should exercise the real provider path by default, but only
    # when the caller did not already choose the runtime/provider explicitly.
    export WINOE_SCENARIO_GENERATION_RUNTIME_MODE="${WINOE_SCENARIO_GENERATION_RUNTIME_MODE:-real}"
    export WINOE_SCENARIO_GENERATION_PROVIDER="${WINOE_SCENARIO_GENERATION_PROVIDER:-anthropic}"
    export WINOE_SCENARIO_GENERATION_MODEL="${WINOE_SCENARIO_GENERATION_MODEL:-claude-opus-4-6}"
  fi
}

require_database_config() {
  if [[ -z "${WINOE_DATABASE_URL:-}" && -z "${WINOE_DATABASE_URL_SYNC:-}" ]]; then
    log_error "ERROR: Winoe database configuration is missing."
    exit 1
  fi
}

stop_children() {
  local pid
  for pid in "${RUNNING_PIDS[@]:-}"; do
    if [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done
  for pid in "${RUNNING_PIDS[@]:-}"; do
    if [[ -n "${pid:-}" ]]; then
      wait "$pid" 2>/dev/null || true
    fi
  done
}

on_signal() {
  local exit_code="$1"
  SUPERVISOR_SHUTTING_DOWN=1
  SUPERVISOR_EXIT_CODE="$exit_code"
  stop_children
}

on_exit() {
  stop_children
}

install_poetry_if_needed() {
  if command -v "$POETRY_CMD" &>/dev/null; then
    USE_POETRY=1
    return
  fi

  log_info "Winoe worker launcher: Poetry not found, attempting install."
  local install_status=0
  if command -v pipx &>/dev/null; then
    pipx install poetry || install_status=$?
    export PATH="$HOME/.local/bin:$PATH"
  elif command -v python3 &>/dev/null; then
    local venv_dir="${PROJECT_ROOT}/.venv-poetry"
    python3 -m venv "$venv_dir" || install_status=$?
    if [[ $install_status -eq 0 ]]; then
      "$venv_dir/bin/pip" install poetry || install_status=$?
    fi
    POETRY_CMD="$venv_dir/bin/poetry"
  else
    install_status=1
  fi

  if [[ $install_status -eq 0 ]] && { command -v "$POETRY_CMD" &>/dev/null || [[ -x "$POETRY_CMD" ]]; }; then
    USE_POETRY=1
  elif [[ -x "${PROJECT_ROOT}/.venv/bin/python" ]]; then
    log_info "Winoe worker launcher: using existing .venv."
    export PATH="${PROJECT_ROOT}/.venv/bin:$PATH"
  else
    log_error "ERROR: Poetry install failed and no .venv was found."
    exit 1
  fi
}

configure_runtime() {
  install_poetry_if_needed
  if [[ $USE_POETRY -eq 1 ]]; then
    RUN_PREFIX=("$POETRY_CMD" run)
  fi
}

run_api() {
  load_environment
  apply_local_defaults
  require_database_config

  local reload_flag=()
  if [[ "${WINOE_ENV:-local}" == "local" && "${DISABLE_RELOAD:-0}" != "1" ]]; then
    reload_flag=(--reload)
  fi

  log_info "Starting Winoe API server."
  exec "${RUN_PREFIX[@]}" uvicorn app.api.main:app "${reload_flag[@]}" --host 0.0.0.0 --port 8000
}

run_worker() {
  load_environment
  apply_local_defaults
  require_database_config

  log_info "Starting Winoe worker."
  exec "${RUN_PREFIX[@]}" python -m app.shared.jobs.shared_jobs_worker_cli_service worker
}

run_migrations() {
  load_environment
  require_database_config

  log_info "Running Winoe database migrations."
  exec "${RUN_PREFIX[@]}" alembic upgrade head
}

run_local_bootstrap() {
  load_environment
  apply_local_defaults
  # Seed data should not depend on auth bypass state from the caller.
  export DEV_AUTH_BYPASS=0
  require_database_config

  log_info "Bootstrapping Winoe local demo seed data."
  export PYTHONPATH="${PROJECT_ROOT}${PYTHONPATH:+:$PYTHONPATH}"
  "${RUN_PREFIX[@]}" alembic upgrade head
  exec "${RUN_PREFIX[@]}" python scripts/seed_local_talent_partners.py --reset
}

run_dead_letter_retry() {
  load_environment
  require_database_config

  log_info "Retrying dead-letter Winoe jobs."
  exec "${RUN_PREFIX[@]}" python -m app.shared.jobs.shared_jobs_worker_cli_service retry-dead-jobs "$@"
}

run_tests() {
  load_environment
  log_info "Running Winoe tests."
  exec "${RUN_PREFIX[@]}" pytest -q
}

run_supervised_local_runtime() {
  load_environment
  apply_local_defaults
  require_database_config

  local api_pid=""
  local worker_pid=""
  RUNNING_PIDS=()
  SUPERVISOR_SHUTTING_DOWN=0
  SUPERVISOR_EXIT_CODE=0

  trap 'on_signal 130' INT
  trap 'on_signal 143' TERM
  trap 'on_exit' EXIT

  log_info "Starting Winoe API server and worker."
  if [[ "${WINOE_ENV:-local}" == "local" && "${DISABLE_RELOAD:-0}" != "1" ]]; then
    "${RUN_PREFIX[@]}" uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000 &
  else
    "${RUN_PREFIX[@]}" uvicorn app.api.main:app --host 0.0.0.0 --port 8000 &
  fi
  api_pid="$!"

  "${RUN_PREFIX[@]}" python -m app.shared.jobs.shared_jobs_worker_cli_service worker &
  worker_pid="$!"

  RUNNING_PIDS=("$api_pid" "$worker_pid")

  while true; do
    if ! kill -0 "$api_pid" 2>/dev/null; then
      wait "$api_pid" || api_exit_code=$?
      api_exit_code="${api_exit_code:-0}"
      if [[ $SUPERVISOR_SHUTTING_DOWN -eq 0 ]]; then
        log_error "ERROR: Winoe API server exited unexpectedly with status ${api_exit_code}."
        SUPERVISOR_SHUTTING_DOWN=1
        SUPERVISOR_EXIT_CODE=1
        stop_children
      fi
      break
    fi

    if ! kill -0 "$worker_pid" 2>/dev/null; then
      wait "$worker_pid" || worker_exit_code=$?
      worker_exit_code="${worker_exit_code:-0}"
      if [[ $SUPERVISOR_SHUTTING_DOWN -eq 0 ]]; then
        log_error "ERROR: Winoe worker exited unexpectedly with status ${worker_exit_code}."
        SUPERVISOR_SHUTTING_DOWN=1
        SUPERVISOR_EXIT_CODE=1
        stop_children
      fi
      break
    fi

    sleep 1
  done

  stop_children
  exit "$SUPERVISOR_EXIT_CODE"
}

main() {
  configure_runtime

  local command="${1:-up}"
  shift || true

  case "$command" in
    up|local|default)
      run_supervised_local_runtime
      ;;
    api)
      run_api
      ;;
    worker)
      run_worker
      ;;
    migrate)
      run_migrations
      ;;
    bootstrap-local)
      run_local_bootstrap
      ;;
    retry-dead-jobs)
      run_dead_letter_retry "$@"
      ;;
    test)
      run_tests
      ;;
    *)
      log_error "Usage: ./runBackend.sh [up|api|worker|migrate|bootstrap-local|retry-dead-jobs|test]"
      exit 1
      ;;
  esac
}

main "$@"
