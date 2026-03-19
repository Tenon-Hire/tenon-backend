#!/usr/bin/env bash
set -euo pipefail

###############################################################################
# Tenon AI - Service & Logic QA Runner
#
# Runs backend service/logic QA in the required order:
#   1) Existing tests (no coverage addopts)
#   2) Existing tests with coverage
#   3) Combined tests directory with coverage (optional)
#   4) Strict validation gates on coverage JSON:
#      - branch coverage enabled and above threshold
#      - zero missing lines in app/services/**
#      - all top-level public service functions executed
#
# Writes logs/results under:
#   /qa_verifications/Service-Logic-QA/service_logic_qa_latest/
# (overwritten on each run)
#
# Usage:
#   ./qa_verifications/Service-Logic-QA/run-service-logic-qa.sh
#   ./qa_verifications/Service-Logic-QA/run-service-logic-qa.sh --skip-combined
#   ./qa_verifications/Service-Logic-QA/run-service-logic-qa.sh --branch-min 97
#   ./qa_verifications/Service-Logic-QA/run-service-logic-qa.sh --no-strict
###############################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
QA_ROOT="$BACKEND_ROOT/qa_verifications/Service-Logic-QA"
RESULTS_DIR="$QA_ROOT/service_logic_qa_latest"
REPORT_MD="$RESULTS_DIR/service_logic_qa_report.md"
ARTIFACTS_DIR="$RESULTS_DIR/artifacts"
LOG_DIR="$ARTIFACTS_DIR/logs"

SKIP_COMBINED=0
STRICT_ENFORCEMENT=1
BRANCH_MIN=99
STRICT_STATUS="NOT_RUN"
STRICT_SOURCE_JSON=""
STRICT_REPORT_FILE=""
RUN_MODE="full"
OVERALL_STATUS="PASS"
STEP_01_STATUS="NOT_RUN"
STEP_02_STATUS="NOT_RUN"
STEP_03_STATUS="NOT_RUN"
STEP_01_DURATION_S="0"
STEP_02_DURATION_S="0"
STEP_03_DURATION_S="0"
STEP_04_DURATION_S="0"
RUN_FINISHED_UTC=""
LAST_STEP_DURATION_S="0"
RUN_STARTED_EPOCH="0"

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; }
headr() { echo -e "\n${BOLD}━━━ $* ━━━${NC}\n"; }

usage() {
  cat <<EOF
Usage: $0 [options]

Options:
  --skip-combined      Skip combined coverage run (tests directory)
  --branch-min <pct>   Minimum app/services branch coverage percent for strict gate (default: $BRANCH_MIN)
  --no-strict          Disable strict post-run validation gates
  -h, --help           Show help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-combined)
      SKIP_COMBINED=1
      RUN_MODE="custom"
      shift
      ;;
    --branch-min)
      [[ $# -lt 2 ]] && { fail "--branch-min requires a value"; exit 1; }
      BRANCH_MIN="$2"
      RUN_MODE="custom"
      shift 2
      ;;
    --no-strict)
      STRICT_ENFORCEMENT=0
      RUN_MODE="custom"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "Unknown argument: $1"
      usage
      exit 1
      ;;
  esac
done

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    fail "Required command not found: $1"
    exit 1
  fi
}

run_step() {
  local label="$1"
  local cmd="$2"
  local log_file="$LOG_DIR/${label}.log"
  local start_ts end_ts duration
  start_ts="$(date +%s)"
  info "Running: $label"
  set +e
  bash -lc "$cmd" 2>&1 | tee "$log_file"
  local rc=${PIPESTATUS[0]}
  set -e
  end_ts="$(date +%s)"
  duration=$((end_ts - start_ts))
  LAST_STEP_DURATION_S="$duration"
  if [[ $rc -ne 0 ]]; then
    fail "$label failed (exit=$rc, duration=${duration}s). See $log_file"
    return $rc
  fi
  ok "$label passed (duration=${duration}s)."
  return 0
}

extract_summary_line() {
  local log_file="$1"
  if [[ ! -f "$log_file" ]]; then
    echo "not-run"
    return 0
  fi
  if rg -q "Required test coverage of .* not reached" "$log_file"; then
    rg -n "Required test coverage of .* not reached" "$log_file" | tail -n 1 | sed 's/^[0-9]*://'
    return 0
  fi
  rg -n "={3,} .* (passed|failed|error|errors|skipped)" "$log_file" | tail -n 1 | sed 's/^[0-9]*://' || true
}

md_escape_cell() {
  printf '%s' "$1" | tr '\n' ' ' | sed 's/|/\\|/g'
}

strict_validate_coverage() {
  local coverage_json="$1"
  STRICT_REPORT_FILE="$ARTIFACTS_DIR/strict-validation.txt"
  STRICT_SOURCE_JSON="$coverage_json"

  if [[ ! -f "$coverage_json" ]]; then
    STRICT_STATUS="FAIL"
    fail "Strict validation failed: coverage JSON not found: $coverage_json"
    return 1
  fi

  if ! COVERAGE_JSON="$coverage_json" \
  BACKEND_ROOT="$BACKEND_ROOT" \
  BRANCH_MIN="$BRANCH_MIN" \
  STRICT_REPORT_FILE="$STRICT_REPORT_FILE" \
  python3 - <<'PY'
import ast
import json
import os
from pathlib import Path

coverage_path = Path(os.environ["COVERAGE_JSON"])
backend_root = Path(os.environ["BACKEND_ROOT"])
branch_min = float(os.environ["BRANCH_MIN"])
report_path = Path(os.environ["STRICT_REPORT_FILE"])

cov = json.loads(coverage_path.read_text())
service_prefix = "app/services/"
service_files = {
    file_path: file_data
    for file_path, file_data in cov.get("files", {}).items()
    if file_path.startswith(service_prefix)
}
if not service_files:
    report_path.write_text(
        "strict_status=fail\n"
        "reason=no_service_files_in_coverage\n"
        "hint=Coverage JSON must include app/services/** files.\n"
    )
    raise SystemExit(20)

num_branches = 0
covered_branches = 0
for file_data in service_files.values():
    summary = file_data.get("summary", {})
    num_branches += int(summary.get("num_branches", 0) or 0)
    covered_branches += int(summary.get("covered_branches", 0) or 0)

if num_branches <= 0:
    report_path.write_text(
        "strict_status=fail\n"
        "reason=service_num_branches_is_zero\n"
        "hint=Service coverage JSON has no branch counters.\n"
    )
    raise SystemExit(21)

branch_pct = covered_branches / num_branches * 100.0
if branch_pct < branch_min:
    report_path.write_text(
        "strict_status=fail\n"
        "reason=service_branch_coverage_below_threshold\n"
        "scope=app/services/**\n"
        f"branch_pct={branch_pct:.2f}\n"
        f"branch_min={branch_min:.2f}\n"
        f"covered_branches={covered_branches}\n"
        f"num_branches={num_branches}\n"
    )
    raise SystemExit(22)

service_missing_lines = []
for file_path, file_data in service_files.items():
    summary = file_data.get("summary", {})
    missing = int(summary.get("missing_lines", 0) or 0)
    if missing > 0:
        missing_lines = file_data.get("missing_lines", []) or []
        service_missing_lines.append((file_path, missing, missing_lines))

if service_missing_lines:
    lines = [
        "strict_status=fail",
        "reason=services_have_missing_lines",
        f"service_files_with_missing={len(service_missing_lines)}",
    ]
    for path, missing_count, missing_lines in sorted(service_missing_lines):
        preview = ",".join(str(n) for n in missing_lines[:12])
        suffix = "..." if len(missing_lines) > 12 else ""
        lines.append(f"{path} missing={missing_count} lines={preview}{suffix}")
    report_path.write_text("\n".join(lines) + "\n")
    raise SystemExit(23)

service_root = backend_root / "app" / "services"
unexecuted_public_functions = []

for py_path in sorted(service_root.rglob("*.py")):
    rel = py_path.relative_to(backend_root).as_posix()
    module = ast.parse(py_path.read_text(encoding="utf-8"), filename=str(py_path))
    public_funcs = [
        node.name
        for node in module.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    ]
    if not public_funcs:
        continue

    cov_file = cov.get("files", {}).get(rel, {})
    fn_cov = cov_file.get("functions", {})
    for fn_name in public_funcs:
        summary = (fn_cov.get(fn_name) or {}).get("summary") or {}
        covered_lines = int(summary.get("covered_lines", 0) or 0)
        if covered_lines <= 0:
            unexecuted_public_functions.append((rel, fn_name))

if unexecuted_public_functions:
    lines = [
        "strict_status=fail",
        "reason=public_service_functions_not_executed",
        f"unexecuted_count={len(unexecuted_public_functions)}",
    ]
    for rel, fn_name in unexecuted_public_functions[:200]:
        lines.append(f"{rel}::{fn_name}")
    if len(unexecuted_public_functions) > 200:
        lines.append(f"... truncated {len(unexecuted_public_functions) - 200} entries")
    report_path.write_text("\n".join(lines) + "\n")
    raise SystemExit(24)

report_path.write_text(
    "strict_status=pass\n"
    "scope=app/services/**\n"
    f"branch_pct={branch_pct:.2f}\n"
    f"branch_min={branch_min:.2f}\n"
    f"covered_branches={covered_branches}\n"
    f"num_branches={num_branches}\n"
    "service_missing_line_files=0\n"
    "unexecuted_public_service_functions=0\n"
)
PY
  then
    STRICT_STATUS="FAIL"
    fail "Strict validation failed (report: $STRICT_REPORT_FILE)."
    return 1
  fi

  STRICT_STATUS="PASS"
  ok "Strict validation passed (report: $STRICT_REPORT_FILE)."
  return 0
}

write_run_summary() {
  local summary_md="$REPORT_MD"
  local started_utc="$1"
  local finished_utc
  local total_duration_s
  local step_01_detail step_02_detail step_03_detail
  local step_03_log strict_status strict_log strict_detail
  local failure_lines=()
  finished_utc="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  RUN_FINISHED_UTC="$finished_utc"
  total_duration_s="$(( $(date +%s) - RUN_STARTED_EPOCH ))"
  step_01_detail="$(extract_summary_line "$LOG_DIR/01-existing-tests.log")"
  step_02_detail="$(extract_summary_line "$LOG_DIR/02-existing-coverage.log")"
  step_03_detail="$(extract_summary_line "$LOG_DIR/03-combined-coverage.log")"

  if [[ $SKIP_COMBINED -eq 0 ]]; then
    step_03_log="[03-combined-coverage.log](artifacts/logs/03-combined-coverage.log)"
  else
    STEP_03_STATUS="SKIPPED"
    step_03_log="-"
    step_03_detail="Skipped by --skip-combined"
  fi

  if [[ $STRICT_ENFORCEMENT -eq 1 ]]; then
    strict_status="$STRICT_STATUS"
    if [[ -f "$STRICT_REPORT_FILE" ]]; then
      strict_log="[strict-validation.txt](artifacts/strict-validation.txt)"
    else
      strict_log="-"
    fi
    strict_detail="branch_min=${BRANCH_MIN}, source=$(basename "$STRICT_SOURCE_JSON")"
  else
    strict_status="SKIPPED"
    strict_log="-"
    strict_detail="Disabled by --no-strict"
  fi

  if [[ "$STEP_01_STATUS" == "FAIL" ]]; then
    failure_lines+=("- Step \`01_existing_tests\` failed. See \`artifacts/logs/01-existing-tests.log\`.")
  fi
  if [[ "$STEP_02_STATUS" == "FAIL" ]]; then
    failure_lines+=("- Step \`02_existing_coverage\` failed. See \`artifacts/logs/02-existing-coverage.log\`.")
  fi
  if [[ "$STEP_03_STATUS" == "FAIL" ]]; then
    failure_lines+=("- Step \`03_combined_coverage\` failed. See \`artifacts/logs/03-combined-coverage.log\`.")
  fi
  if [[ "$strict_status" == "FAIL" ]]; then
    failure_lines+=("- Step \`04_strict_validation\` failed. See \`artifacts/strict-validation.txt\`.")
  fi

  {
    echo "# Service-Logic QA Verification"
    echo
    echo "## Run Summary"
    echo
    echo "- Started (UTC): \`$started_utc\`"
    echo "- Finished (UTC): \`$finished_utc\`"
    echo "- Overall status: \`$OVERALL_STATUS\`"
    echo "- Runner: \`./qa_verifications/Service-Logic-QA/run-service-logic-qa.sh\`"
    echo "- Run mode: \`$RUN_MODE\`"
    echo
    echo "## Artifact Layout"
    echo
    echo "- \`artifacts/logs/\`: pytest command logs"
    echo "- \`artifacts/coverage-existing.json\`: coverage from existing tests run"
    if [[ $SKIP_COMBINED -eq 0 ]]; then
      echo "- \`artifacts/coverage-combined.json\`: coverage from combined tests run"
    else
      echo "- \`artifacts/coverage-combined.json\`: skipped (\`--skip-combined\`)"
    fi
    if [[ -f "$STRICT_REPORT_FILE" ]]; then
      echo "- \`artifacts/strict-validation.txt\`: strict gate report"
    else
      echo "- \`artifacts/strict-validation.txt\`: not generated"
    fi
    echo "- Branch minimum (%): \`$BRANCH_MIN\`"
    echo "- Strict enforcement: \`$STRICT_ENFORCEMENT\`"
    echo
    echo "## Step Results"
    echo
    echo "| Step | Status | Log | Details |"
    echo "|---|---|---|---|"
    echo "| \`01_existing_tests\` | \`$STEP_01_STATUS\` | [01-existing-tests.log](artifacts/logs/01-existing-tests.log) | $(md_escape_cell "$step_01_detail") |"
    echo "| \`02_existing_coverage\` | \`$STEP_02_STATUS\` | [02-existing-coverage.log](artifacts/logs/02-existing-coverage.log) | $(md_escape_cell "$step_02_detail") |"
    echo "| \`03_combined_coverage\` | \`$STEP_03_STATUS\` | $step_03_log | $(md_escape_cell "$step_03_detail") |"
    echo "| \`04_strict_validation\` | \`$strict_status\` | $strict_log | $(md_escape_cell "$strict_detail") |"
    echo
    echo "## Timing"
    echo
    echo "- Total duration (s): \`$total_duration_s\`"
    echo "- 01_existing_tests duration (s): \`$STEP_01_DURATION_S\`"
    echo "- 02_existing_coverage duration (s): \`$STEP_02_DURATION_S\`"
    echo "- 03_combined_coverage duration (s): \`$STEP_03_DURATION_S\`"
    echo "- 04_strict_validation duration (s): \`$STEP_04_DURATION_S\`"
    echo
    echo "## Failures"
    echo
    if [[ "${#failure_lines[@]}" -eq 0 ]]; then
      echo "- None"
    else
      printf '%s\n' "${failure_lines[@]}"
    fi
  } >"$summary_md"
}

main() {
  require_cmd poetry
  require_cmd rg
  require_cmd python3

  # Keep a single latest artifact set by clearing this directory every run.
  if [[ "$RESULTS_DIR" != "$QA_ROOT/service_logic_qa_latest" ]]; then
    fail "Unexpected results directory path: $RESULTS_DIR"
    exit 1
  fi
  rm -rf "$RESULTS_DIR"
  mkdir -p "$LOG_DIR"
  local started_utc
  started_utc="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  RUN_STARTED_EPOCH="$(date +%s)"

  headr "Service & Logic QA"
  info "Results directory: $RESULTS_DIR"

  cd "$BACKEND_ROOT"

  if ! run_step \
    "01-existing-tests" \
    "poetry run pytest -o addopts=''"; then
    STEP_01_DURATION_S="$LAST_STEP_DURATION_S"
    STEP_01_STATUS="FAIL"
    OVERALL_STATUS="FAIL"
  else
    STEP_01_DURATION_S="$LAST_STEP_DURATION_S"
    STEP_01_STATUS="PASS"
  fi

  if ! run_step \
    "02-existing-coverage" \
    "poetry run pytest -o addopts='' --cov=app --cov-branch --cov-report=term-missing --cov-report=xml --cov-report=json:$ARTIFACTS_DIR/coverage-existing.json"; then
    STEP_02_DURATION_S="$LAST_STEP_DURATION_S"
    STEP_02_STATUS="FAIL"
    OVERALL_STATUS="FAIL"
  else
    STEP_02_DURATION_S="$LAST_STEP_DURATION_S"
    STEP_02_STATUS="PASS"
  fi

  if [[ $SKIP_COMBINED -eq 0 ]]; then
    if ! run_step \
      "03-combined-coverage" \
      "poetry run pytest -o addopts='' tests --cov=app --cov-branch --cov-report=term-missing --cov-report=xml --cov-report=json:$ARTIFACTS_DIR/coverage-combined.json"; then
      STEP_03_DURATION_S="$LAST_STEP_DURATION_S"
      STEP_03_STATUS="FAIL"
      OVERALL_STATUS="FAIL"
    else
      STEP_03_DURATION_S="$LAST_STEP_DURATION_S"
      STEP_03_STATUS="PASS"
    fi
  else
    warn "Skipping combined run by flag."
    STEP_03_DURATION_S="0"
    STEP_03_STATUS="SKIPPED"
  fi

  if [[ $STRICT_ENFORCEMENT -eq 1 ]]; then
    local strict_start_ts strict_end_ts
    strict_start_ts="$(date +%s)"
    local strict_source_json
    if [[ $SKIP_COMBINED -eq 0 ]]; then
      strict_source_json="$ARTIFACTS_DIR/coverage-combined.json"
    else
      strict_source_json="$ARTIFACTS_DIR/coverage-existing.json"
    fi
    if ! strict_validate_coverage "$strict_source_json"; then
      OVERALL_STATUS="FAIL"
    fi
    strict_end_ts="$(date +%s)"
    STEP_04_DURATION_S="$((strict_end_ts - strict_start_ts))"
  else
    STRICT_STATUS="SKIPPED"
    STEP_04_DURATION_S="0"
  fi

  write_run_summary "$started_utc"
  if [[ "$OVERALL_STATUS" == "FAIL" ]]; then
    fail "Service & Logic QA completed with failures."
    info "Report: $REPORT_MD"
    exit 1
  fi
  ok "Service & Logic QA completed."
  info "Report: $REPORT_MD"
}

main "$@"
