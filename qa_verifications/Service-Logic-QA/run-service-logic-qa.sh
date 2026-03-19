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
#   ./run-service-logic-qa.sh
#   ./run-service-logic-qa.sh --skip-combined
#   ./run-service-logic-qa.sh --branch-min 97
#   ./run-service-logic-qa.sh --no-strict
###############################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
QA_ROOT="$BACKEND_ROOT/qa_verifications/Service-Logic-QA"
RESULTS_DIR="$QA_ROOT/service_logic_qa_latest"
LOG_DIR="$RESULTS_DIR/logs"

SKIP_COMBINED=0
STRICT_ENFORCEMENT=1
BRANCH_MIN=99
STRICT_STATUS="not-run"
STRICT_SOURCE_JSON=""
STRICT_REPORT_FILE=""
OVERALL_STATUS="pass"
STEP_01_STATUS="not-run"
STEP_02_STATUS="not-run"
STEP_03_STATUS="not-run"

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
      shift
      ;;
    --branch-min)
      [[ $# -lt 2 ]] && { fail "--branch-min requires a value"; exit 1; }
      BRANCH_MIN="$2"
      shift 2
      ;;
    --no-strict)
      STRICT_ENFORCEMENT=0
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

strict_validate_coverage() {
  local coverage_json="$1"
  STRICT_REPORT_FILE="$RESULTS_DIR/strict-validation.txt"
  STRICT_SOURCE_JSON="$coverage_json"

  if [[ ! -f "$coverage_json" ]]; then
    STRICT_STATUS="fail"
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
    STRICT_STATUS="fail"
    fail "Strict validation failed (report: $STRICT_REPORT_FILE)."
    return 1
  fi

  STRICT_STATUS="pass"
  ok "Strict validation passed (report: $STRICT_REPORT_FILE)."
  return 0
}

write_run_summary() {
  local summary_md="$RESULTS_DIR/README.md"
  local started_utc="$1"
  local finished_utc
  finished_utc="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"

  {
    echo "# Service & Logic QA Runner Results"
    echo
    echo "- Started (UTC): \`$started_utc\`"
    echo "- Finished (UTC): \`$finished_utc\`"
    echo "- Overall status: \`$OVERALL_STATUS\`"
    echo "- Backend root: \`$BACKEND_ROOT\`"
    echo "- Runner: \`$0\`"
    echo
    echo "## Commands"
    echo
    echo "1. \`poetry run pytest -o addopts=''\`"
    echo "2. \`poetry run pytest -o addopts='' --cov=app --cov-branch --cov-report=term-missing --cov-report=xml --cov-report=json:$RESULTS_DIR/coverage-existing.json\`"
    if [[ $SKIP_COMBINED -eq 0 ]]; then
      echo "3. \`poetry run pytest -o addopts='' tests --cov=app --cov-branch --cov-report=term-missing --cov-report=xml --cov-report=json:$RESULTS_DIR/coverage-combined.json\`"
    else
      echo "3. Skipped (\`--skip-combined\`)"
    fi
    echo
    echo "## Summary"
    echo
    echo "- Existing tests: [$STEP_01_STATUS] $(extract_summary_line "$LOG_DIR/01-existing-tests.log")"
    echo "- Existing coverage run: [$STEP_02_STATUS] $(extract_summary_line "$LOG_DIR/02-existing-coverage.log")"
    if [[ $SKIP_COMBINED -eq 0 ]]; then
      echo "- Combined coverage run: [$STEP_03_STATUS] $(extract_summary_line "$LOG_DIR/03-combined-coverage.log")"
    fi
    if [[ $STRICT_ENFORCEMENT -eq 1 ]]; then
      echo "- Strict validation: $STRICT_STATUS"
    else
      echo "- Strict validation: skipped (\`--no-strict\`)"
    fi
    echo
    echo "## Artifacts"
    echo
    echo "- Logs: \`$LOG_DIR\`"
    echo "- Existing coverage JSON: \`$RESULTS_DIR/coverage-existing.json\`"
    if [[ $SKIP_COMBINED -eq 0 ]]; then
      echo "- Combined coverage JSON: \`$RESULTS_DIR/coverage-combined.json\`"
    fi
    if [[ -n "$STRICT_REPORT_FILE" ]]; then
      echo "- Strict validation report: \`$STRICT_REPORT_FILE\`"
      if [[ -n "$STRICT_SOURCE_JSON" ]]; then
        echo "- Strict validation source JSON: \`$STRICT_SOURCE_JSON\`"
      fi
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

  headr "Service & Logic QA"
  info "Results directory: $RESULTS_DIR"

  cd "$BACKEND_ROOT"

  if ! run_step \
    "01-existing-tests" \
    "poetry run pytest -o addopts=''"; then
    STEP_01_STATUS="fail"
    OVERALL_STATUS="fail"
  else
    STEP_01_STATUS="pass"
  fi

  if ! run_step \
    "02-existing-coverage" \
    "poetry run pytest -o addopts='' --cov=app --cov-branch --cov-report=term-missing --cov-report=xml --cov-report=json:$RESULTS_DIR/coverage-existing.json"; then
    STEP_02_STATUS="fail"
    OVERALL_STATUS="fail"
  else
    STEP_02_STATUS="pass"
  fi

  if [[ $SKIP_COMBINED -eq 0 ]]; then
    if ! run_step \
      "03-combined-coverage" \
      "poetry run pytest -o addopts='' tests --cov=app --cov-branch --cov-report=term-missing --cov-report=xml --cov-report=json:$RESULTS_DIR/coverage-combined.json"; then
      STEP_03_STATUS="fail"
      OVERALL_STATUS="fail"
    else
      STEP_03_STATUS="pass"
    fi
  else
    warn "Skipping combined run by flag."
    STEP_03_STATUS="skipped"
  fi

  if [[ $STRICT_ENFORCEMENT -eq 1 ]]; then
    local strict_source_json
    if [[ $SKIP_COMBINED -eq 0 ]]; then
      strict_source_json="$RESULTS_DIR/coverage-combined.json"
    else
      strict_source_json="$RESULTS_DIR/coverage-existing.json"
    fi
    if ! strict_validate_coverage "$strict_source_json"; then
      OVERALL_STATUS="fail"
    fi
  else
    STRICT_STATUS="skipped"
  fi

  write_run_summary "$started_utc"
  if [[ "$OVERALL_STATUS" == "fail" ]]; then
    fail "Service & Logic QA completed with failures."
    info "Summary: $RESULTS_DIR/README.md"
    exit 1
  fi
  ok "Service & Logic QA completed."
  info "Summary: $RESULTS_DIR/README.md"
}

main "$@"
