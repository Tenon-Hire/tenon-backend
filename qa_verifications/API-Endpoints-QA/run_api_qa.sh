#!/usr/bin/env bash
###############################################################################
# Winoe AI – Backend QA Runner
#
# Executes the full Postman collection against a running local backend server
# using Newman (the Postman CLI runner).
#
# PREREQUISITES:
#   1. Backend server running on localhost:8000 with:
#        WINOE_ENV=local  DEV_AUTH_BYPASS=1
#      (i.e. `./runBackend.sh` was executed successfully)
#   2. Newman installed:  npm install -g newman
#      (optional HTML reports: npm install -g newman-reporter-htmlextra)
#
# USAGE:
#   ./qa_verifications/API-Endpoints-QA/run_api_qa.sh                  # full collection
#   ./qa_verifications/API-Endpoints-QA/run_api_qa.sh --e2e            # E2E happy path only
#   ./qa_verifications/API-Endpoints-QA/run_api_qa.sh --folder "01"    # single folder by prefix
#   ./qa_verifications/API-Endpoints-QA/run_api_qa.sh --bail           # stop on first failure
#   ./qa_verifications/API-Endpoints-QA/run_api_qa.sh --verbose        # extra request/response logging
#
# ENVIRONMENT OVERRIDES (optional):
#   BASE_URL=http://localhost:9000  ./qa_verifications/API-Endpoints-QA/run_api_qa.sh
#   TALENT_PARTNER_EMAIL=custom@co.com  ./qa_verifications/API-Endpoints-QA/run_api_qa.sh
#   ADMIN_API_KEY=secret           ./qa_verifications/API-Endpoints-QA/run_api_qa.sh
###############################################################################
set -euo pipefail

# ─── Paths ───────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COLLECTION="$SCRIPT_DIR/winoe-backend-qa-postman-collection.json"
ENVIRONMENT="$SCRIPT_DIR/winoe-backend-qa-postman-environment.json"
LATEST_DIR="$SCRIPT_DIR/api_qa_latest"
REPORT_MD="$LATEST_DIR/api_endpoints_qa_report.md"
ARTIFACTS_DIR="$LATEST_DIR/artifacts"
LOG_DIR="$ARTIFACTS_DIR/logs"
TMP_REPORT_JSON="$ARTIFACTS_DIR/newman_report.json"
HTML_REPORT="$ARTIFACTS_DIR/newman_report.html"
CONTRACT_LOG="$LOG_DIR/00_collection_contract.log"
NEWMAN_LOG="$LOG_DIR/01_newman_run.log"
RUN_STARTED_UTC="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

# ─── Defaults (match runBackend.sh seed data) ────────────────────────────────
BASE_URL="${BASE_URL:-http://localhost:8000}"
TALENT_PARTNER_EMAIL="${TALENT_PARTNER_EMAIL:-talent_partner1@local.test}"
TALENT_PARTNER_TOKEN="${TALENT_PARTNER_TOKEN:-talent_partner:${TALENT_PARTNER_EMAIL}}"
CANDIDATE_EMAIL="${CANDIDATE_EMAIL:-e2e-candidate@test.com}"
CANDIDATE_TOKEN="${CANDIDATE_TOKEN:-candidate:${CANDIDATE_EMAIL}}"
ADMIN_API_KEY="${ADMIN_API_KEY:-my-super-secret-admin-key}"
TIMEOUT_MS="${TIMEOUT_MS:-120000}"

# ─── Colors ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ─── Helpers ─────────────────────────────────────────────────────────────────
info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; }
header(){ echo -e "\n${BOLD}━━━ $* ━━━${NC}\n"; }

# ─── Parse CLI args ─────────────────────────────────────────────────────────
RUN_MODE="full"       # full | e2e | folder
FOLDER_FILTER=""
BAIL=0
VERBOSE=0
DELAY_MS=100          # ms between requests

while [[ $# -gt 0 ]]; do
    case "$1" in
        --e2e)       RUN_MODE="e2e";  shift ;;
        --folder)    RUN_MODE="folder"; FOLDER_FILTER="$2"; shift 2 ;;
        --bail)      BAIL=1; shift ;;
        --verbose)   VERBOSE=1; shift ;;
        --delay)     DELAY_MS="$2"; shift 2 ;;
        --timeout)   TIMEOUT_MS="$2"; shift 2 ;;
        --help|-h)
            echo "Usage: $0 [--e2e] [--folder PREFIX] [--bail] [--verbose] [--delay MS] [--timeout MS]"
            echo ""
            echo "Modes:"
            echo "  (default)        Run all 93 requests across all 18 folders"
            echo "  --e2e            Run only the E2E happy path folder (99)"
            echo "  --folder PREFIX  Run a single folder by name prefix (e.g. '02', '05')"
            echo ""
            echo "Options:"
            echo "  --bail           Stop on first test failure"
            echo "  --verbose        Show request/response bodies in output"
            echo "  --delay MS       Delay between requests (default: 100)"
            echo "  --timeout MS     Request timeout (default: 120000)"
            echo ""
            echo "Environment variables:"
            echo "  BASE_URL          Server URL (default: http://localhost:8000)"
            echo "  TALENT_PARTNER_EMAIL   Seeded talent_partner email (default: talent_partner1@local.test)"
            echo "  CANDIDATE_EMAIL   Candidate email for testing (default: e2e-candidate@test.com)"
            echo "  ADMIN_API_KEY     Admin API key (default: my-super-secret-admin-key)"
            exit 0
            ;;
        *)
            fail "Unknown argument: $1"; exit 1 ;;
    esac
done

# ─── Pre-flight checks ──────────────────────────────────────────────────────
header "Pre-flight Checks"

# Check Newman
if ! command -v newman &>/dev/null; then
    fail "Newman is not installed. Run: npm install -g newman"
    exit 1
fi
ok "Newman $(newman --version) found"

# Check collection/environment files
if [[ ! -f "$COLLECTION" ]]; then
    fail "Collection file not found: $COLLECTION"
    exit 1
fi
if [[ ! -f "$ENVIRONMENT" ]]; then
    fail "Environment file not found: $ENVIRONMENT"
    exit 1
fi
ok "Collection and environment files found"

# Check server is reachable
info "Checking server at ${BASE_URL}/health ..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "${BASE_URL}/health" 2>/dev/null || echo "000")
if [[ "$HTTP_CODE" == "200" ]]; then
    ok "Server is healthy (HTTP $HTTP_CODE)"
else
    fail "Server at ${BASE_URL} is not reachable (HTTP $HTTP_CODE)"
    echo ""
    echo "  Make sure the backend is running:"
    echo "    cd $(dirname "$SCRIPT_DIR")"
    echo "    ./runBackend.sh"
    echo ""
    exit 1
fi

# Recreate latest directory so each run overwrites prior artifacts.
rm -rf "$LATEST_DIR"
mkdir -p "$LOG_DIR"

header "Collection Contract Checks"
info "Validating endpoint coverage and Postman test scripts..."
set +e
python3 - "$COLLECTION" "$BASE_URL" <<'PY' | tee "$CONTRACT_LOG"
import json
import re
import sys
import urllib.error
import urllib.request

collection_path = sys.argv[1]
base_url = sys.argv[2].rstrip("/")
openapi_url = f"{base_url}/openapi.json"


def normalize_collection_path(raw: str) -> str:
    path = raw.replace("{{base_url}}", "")
    if not path.startswith("/"):
        # Handles raw values like "{{base_url}}/api/..." and plain "/api/..."
        idx = path.find("/")
        path = path[idx:] if idx >= 0 else "/" + path
    path = path.split("?", 1)[0]
    path = re.sub(r"\{\{[^}]+\}\}", "{var}", path)
    path = re.sub(r":([A-Za-z_][A-Za-z0-9_]*)", "{var}", path)
    path = re.sub(r"/{2,}", "/", path)
    return path.rstrip("/") or "/"


def normalize_server_path(path: str) -> str:
    path = re.sub(r"\{[^}/]+\}", "{var}", path)
    path = re.sub(r"/{2,}", "/", path)
    return path.rstrip("/") or "/"


def server_regex(path: str) -> re.Pattern[str]:
    expr = re.escape(path)
    expr = re.sub(r"\\\{[^}/]+\\\}", r"[^/]+", expr)
    return re.compile(rf"^{expr}$")


def walk_items(items, out):
    for item in items:
        if "request" in item:
            req = item["request"]
            method = req.get("method", "").upper()
            url = req.get("url", {})
            if isinstance(url, str):
                raw = url
            else:
                raw = url.get("raw") or ""
                if not raw:
                    path_parts = url.get("path", [])
                    if isinstance(path_parts, list):
                        raw = "/" + "/".join(str(p) for p in path_parts)
                    else:
                        raw = str(path_parts)
            events = item.get("event", [])
            out.append(
                {
                    "name": item.get("name", ""),
                    "method": method,
                    "path": normalize_collection_path(raw),
                    "events": events,
                }
            )
        if "item" in item:
            walk_items(item["item"], out)


with open(collection_path, "r", encoding="utf-8") as f:
    collection = json.load(f)

requests = []
walk_items(collection.get("item", []), requests)

missing_post_scripts = []
missing_status_assertions = []
for req in requests:
    test_events = [e for e in req["events"] if e.get("listen") == "test"]
    lines = []
    for event in test_events:
        lines.extend(event.get("script", {}).get("exec") or [])
    script_text = "\n".join(lines)
    if "pm.test(" not in script_text:
        missing_post_scripts.append(f'{req["method"]} {req["path"]} :: {req["name"]}')
    has_status_assertion = (
        "pm.response.to.have.status" in script_text
        or "pm.response.code" in script_text
    )
    if not has_status_assertion:
        missing_status_assertions.append(
            f'{req["method"]} {req["path"]} :: {req["name"]}'
        )

try:
    with urllib.request.urlopen(openapi_url, timeout=8) as response:
        openapi = json.loads(response.read().decode("utf-8"))
except urllib.error.URLError as exc:
    print(f"ERROR: unable to fetch OpenAPI schema from {openapi_url}: {exc}")
    sys.exit(2)

server_routes = set()
for path, methods in openapi.get("paths", {}).items():
    for method in methods:
        m = method.upper()
        if m in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            server_routes.add((m, path))

request_routes = [(r["method"], r["path"]) for r in requests]
missing_routes = []
for method, server_path in sorted(server_routes):
    route_re = server_regex(server_path)
    matched = any(
        req_method == method and route_re.match(req_path)
        for req_method, req_path in request_routes
    )
    if not matched:
        missing_routes.append(f"{method} {normalize_server_path(server_path)}")

print(f"Requests in collection: {len(requests)}")
print(f"Server routes in OpenAPI: {len(server_routes)}")
print(f"Routes covered by collection: {len(server_routes) - len(missing_routes)}/{len(server_routes)}")

if missing_post_scripts:
    print("\nERROR: requests missing post-request test scripts:")
    for item in missing_post_scripts:
        print(f"  - {item}")

if missing_status_assertions:
    print("\nERROR: requests missing status-code assertions in test scripts:")
    for item in missing_status_assertions:
        print(f"  - {item}")

if missing_routes:
    print("\nERROR: backend endpoints missing from collection:")
    for route in missing_routes:
        print(f"  - {route}")

if missing_post_scripts or missing_status_assertions or missing_routes:
    sys.exit(2)
PY
CONTRACT_RC=${PIPESTATUS[0]}
set -e
if [[ $CONTRACT_RC -eq 0 ]]; then
    ok "Collection contract checks passed"
else
    fail "Collection contract checks failed"
    exit 1
fi

# ─── Build Newman command ────────────────────────────────────────────────────
header "Configuration"
info "Base URL:         ${BASE_URL}"
info "TalentPartner:        ${TALENT_PARTNER_EMAIL}"
info "Candidate:        ${CANDIDATE_EMAIL}"
info "Admin key:        ${ADMIN_API_KEY:0:8}..."
info "Run mode:         ${RUN_MODE}"
info "Request delay:    ${DELAY_MS}ms"
info "Request timeout:  ${TIMEOUT_MS}ms"
info "Artifacts:        ${ARTIFACTS_DIR}"
info "Report:           ${REPORT_MD}"
info "Newman log:       ${NEWMAN_LOG}"
[[ $BAIL -eq 1 ]] && info "Bail on failure:  YES"
[[ $VERBOSE -eq 1 ]] && info "Verbose mode:     YES"

# Base newman args
NEWMAN_ARGS=(
    run "$COLLECTION"
    --environment "$ENVIRONMENT"
    --env-var "base_url=${BASE_URL}"
    --env-var "talent_partner_email=${TALENT_PARTNER_EMAIL}"
    --env-var "talent_partner_token=${TALENT_PARTNER_TOKEN}"
    --env-var "candidate_email=${CANDIDATE_EMAIL}"
    --env-var "candidate_token=${CANDIDATE_TOKEN}"
    --env-var "admin_api_key=${ADMIN_API_KEY}"
    --env-var "MAX_RESPONSE_TIME_MS=${TIMEOUT_MS}"
    --delay-request "$DELAY_MS"
    --timeout-request "$TIMEOUT_MS"
    --color on
    --reporters cli,json
    --reporter-json-export "$TMP_REPORT_JSON"
)

# Check for HTML reporter
if newman run --help 2>&1 | grep -q 'htmlextra' || npm list -g newman-reporter-htmlextra &>/dev/null 2>&1; then
    NEWMAN_ARGS+=(--reporters cli,json,htmlextra)
    NEWMAN_ARGS+=(--reporter-htmlextra-export "$HTML_REPORT")
    info "HTML report:      $HTML_REPORT"
fi

# Bail on failure
if [[ $BAIL -eq 1 ]]; then
    NEWMAN_ARGS+=(--bail)
fi

# Verbose
if [[ $VERBOSE -eq 1 ]]; then
    NEWMAN_ARGS+=(--verbose)
fi

# Folder filter
case "$RUN_MODE" in
    e2e)
        NEWMAN_ARGS+=(--folder "99 - Full E2E Happy Path Flow")
        ;;
    folder)
        # Find the folder name that starts with the given prefix
        FOLDER_NAME=$(python3 -c "
import json, sys
with open('$COLLECTION') as f:
    c = json.load(f)
for item in c['item']:
    if item['name'].startswith('$FOLDER_FILTER'):
        print(item['name'])
        sys.exit(0)
print('', end='')
")
        if [[ -z "$FOLDER_NAME" ]]; then
            fail "No folder found matching prefix: $FOLDER_FILTER"
            echo "  Available folders:"
            python3 -c "
import json
with open('$COLLECTION') as f:
    c = json.load(f)
for item in c['item']:
    n = len(item.get('item', []))
    print(f\"    {item['name']}  ({n} requests)\")
"
            exit 1
        fi
        NEWMAN_ARGS+=(--folder "$FOLDER_NAME")
        info "Running folder:   $FOLDER_NAME"
        ;;
esac

# ─── Execute ─────────────────────────────────────────────────────────────────
header "Running Tests"

EXIT_CODE=0
set +e
newman "${NEWMAN_ARGS[@]}" 2>&1 | tee "$NEWMAN_LOG"
EXIT_CODE=${PIPESTATUS[0]}
set -e

# ─── Report Summary ──────────────────────────────────────────────────────────
header "Results"

if [[ -f "$TMP_REPORT_JSON" ]]; then
    python3 - \
        "$TMP_REPORT_JSON" \
        "$REPORT_MD" \
        "$RUN_STARTED_UTC" \
        "$RUN_MODE" \
        "$BASE_URL" \
        "$EXIT_CODE" \
        "$CONTRACT_LOG" \
        "$NEWMAN_LOG" \
        "$HTML_REPORT" <<'PY'
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

json_path = Path(sys.argv[1])
report_path = Path(sys.argv[2])
run_started_utc = sys.argv[3]
run_mode = sys.argv[4]
base_url = sys.argv[5]
exit_code = int(sys.argv[6])
contract_log = Path(sys.argv[7])
newman_log = Path(sys.argv[8])
html_report = Path(sys.argv[9])

with json_path.open(encoding="utf-8") as f:
    report = json.load(f)

run = report.get("run", {})
stats = run.get("stats", {})
timings = run.get("timings", {})

requests = stats.get("requests", {})
assertions = stats.get("assertions", {})
iterations = stats.get("iterations", {})

total_req = int(requests.get("total", 0) or 0)
failed_req = int(requests.get("failed", 0) or 0)
passed_req = total_req - failed_req

total_tests = int(assertions.get("total", 0) or 0)
failed_tests = int(assertions.get("failed", 0) or 0)
passed_tests = total_tests - failed_tests

started_ms = int(timings.get("started", 0) or 0)
completed_ms = int(timings.get("completed", 0) or 0)
duration_ms = max(0, completed_ms - started_ms)
duration_s = duration_ms / 1000

def ms_to_iso(ms: int) -> str | None:
    if ms <= 0:
        return None
    return datetime.fromtimestamp(ms / 1000, tz=UTC).isoformat()

summary = {
    "requests": {"passed": passed_req, "failed": failed_req, "total": total_req},
    "assertions": {"passed": passed_tests, "failed": failed_tests, "total": total_tests},
    "iterations": {
        "passed": int(iterations.get("total", 0) or 0) - int(iterations.get("failed", 0) or 0),
        "failed": int(iterations.get("failed", 0) or 0),
        "total": int(iterations.get("total", 0) or 0),
    },
    "duration_seconds": round(duration_s, 3),
}

timing_block = {
    "started_ms": started_ms,
    "started_utc": ms_to_iso(started_ms),
    "completed_ms": completed_ms,
    "completed_utc": ms_to_iso(completed_ms),
    "duration_ms": duration_ms,
}

failure_items = []
seen = set()
for failure in run.get("failures", []):
    err = failure.get("error", {}) or {}
    source = failure.get("source", {}) or {}
    request_name = source.get("name", "Unknown")
    test_name = err.get("test") or err.get("name") or "Unknown"
    message = err.get("message", "")
    key = (request_name, test_name, message)
    if key in seen:
        continue
    seen.add(key)
    failure_items.append(
        {
            "request": request_name,
            "test": test_name,
            "message": message,
        }
    )

overall_status = "PASS" if exit_code == 0 and failed_tests == 0 else "FAIL"
finished_utc = datetime.now(UTC).isoformat()

def rel_path(path: Path) -> str:
    return path.relative_to(report_path.parent).as_posix()

def md_cell(text: str) -> str:
    return text.replace("|", r"\|").replace("\n", " ")

# Console summary (keeps current UX)
GREEN = "\033[0;32m"
RED = "\033[0;31m"
BOLD = "\033[1m"
NC = "\033[0m"

print(
    f"{BOLD}Requests:{NC}    {GREEN}{passed_req} passed{NC}  /  {total_req} total"
    + (f"  /  {RED}{failed_req} failed{NC}" if failed_req else "")
)
print(
    f"{BOLD}Assertions:{NC}  {GREEN}{passed_tests} passed{NC}  /  {total_tests} total"
    + (f"  /  {RED}{failed_tests} failed{NC}" if failed_tests else "")
)
print(f"{BOLD}Duration:{NC}    {duration_s:.1f}s")

if failure_items:
    print(f"\n{RED}{BOLD}Failed Tests:{NC}")
    for item in failure_items:
        print(f"  {RED}✗{NC} [{item['request']}] {item['test']}")
        if item["message"]:
            print(f"    {item['message'][:200]}")

# Markdown artifact with a uniform layout used by all QA runners.
newman_detail = (
    f"requests={passed_req}/{total_req} passed, "
    f"assertions={passed_tests}/{total_tests} passed, "
    f"duration={duration_s:.1f}s"
)
html_report_line = (
    "- `artifacts/newman_report.html`: Newman HTML report"
    if html_report.exists()
    else "- `artifacts/newman_report.html`: not generated"
)

markdown_lines = [
    "# API-Endpoints QA Verification",
    "",
    "## Run Summary",
    f"- Started (UTC): `{run_started_utc}`",
    f"- Finished (UTC): `{finished_utc}`",
    f"- Overall status: `{overall_status}`",
    f"- Runner: `./qa_verifications/API-Endpoints-QA/run_api_qa.sh`",
    f"- Run mode: `{run_mode}`",
    f"- Base URL: `{base_url}`",
    "",
    "## Artifact Layout",
    "- `artifacts/logs/`: contract + Newman CLI output",
    "- `artifacts/newman_report.json`: Newman raw JSON report",
    html_report_line,
    "",
    "## Step Results",
    "| Step | Status | Log | Details |",
    "|---|---|---|---|",
    (
        f"| `00_collection_contract` | `PASS` | "
        f"[{contract_log.name}]({rel_path(contract_log)}) | "
        f"{md_cell('Validated collection test scripts and OpenAPI endpoint coverage.')} |"
    ),
    (
        f"| `01_newman_run` | `{overall_status}` | "
        f"[{newman_log.name}]({rel_path(newman_log)}) | {md_cell(newman_detail)} |"
    ),
    "",
    "## Newman Summary",
    "```json",
    json.dumps(summary, indent=2),
    "```",
    "",
    "## Timing",
    "```json",
    json.dumps(timing_block, indent=2),
    "```",
    "",
    "## Failures",
    "```json",
    json.dumps(failure_items, indent=2),
    "```",
    "",
]

rendered = "\n".join(markdown_lines)
report_path.write_text(rendered, encoding="utf-8")
PY

    echo -e "${CYAN}Report:${NC}           $REPORT_MD"
    echo -e "${CYAN}Newman JSON:${NC}      $TMP_REPORT_JSON"

    if [[ -f "$HTML_REPORT" ]]; then
        echo -e "${CYAN}HTML report:${NC}      $HTML_REPORT"
    fi
else
    warn "Newman JSON report missing; writing fallback summary."
    {
        echo "# API-Endpoints QA Verification"
        echo
        echo "## Run Summary"
        echo "- Started (UTC): \`$RUN_STARTED_UTC\`"
        echo "- Finished (UTC): \`$(date -u +"%Y-%m-%dT%H:%M:%SZ")\`"
        echo "- Overall status: \`FAIL\`"
        echo "- Runner: \`./qa_verifications/API-Endpoints-QA/run_api_qa.sh\`"
        echo "- Run mode: \`$RUN_MODE\`"
        echo "- Base URL: \`$BASE_URL\`"
        echo
        echo "## Artifact Layout"
        echo "- \`artifacts/logs/\`: contract + Newman CLI output"
        echo "- \`artifacts/newman_report.json\`: not generated"
        echo "- \`artifacts/newman_report.html\`: optional"
        echo
        echo "## Step Results"
        echo "| Step | Status | Log | Details |"
        echo "|---|---|---|---|"
        echo "| \`00_collection_contract\` | \`PASS\` | [$(basename "$CONTRACT_LOG")](artifacts/logs/$(basename "$CONTRACT_LOG")) | Validated collection test scripts and OpenAPI endpoint coverage. |"
        echo "| \`01_newman_run\` | \`FAIL\` | [$(basename "$NEWMAN_LOG")](artifacts/logs/$(basename "$NEWMAN_LOG")) | Newman exited before producing a JSON report. |"
        echo
        echo "## Timing"
        echo "- Started (UTC): \`$RUN_STARTED_UTC\`"
        echo "- Finished (UTC): \`$(date -u +"%Y-%m-%dT%H:%M:%SZ")\`"
        echo
        echo "## Failures"
        echo "- Newman exited before producing \`artifacts/newman_report.json\`."
    } >"$REPORT_MD"
    echo -e "${CYAN}Report:${NC}           $REPORT_MD"
fi

echo ""
if [[ $EXIT_CODE -eq 0 ]]; then
    ok "All tests passed!"
else
    fail "Some tests failed (exit code: $EXIT_CODE)"
fi

exit $EXIT_CODE
