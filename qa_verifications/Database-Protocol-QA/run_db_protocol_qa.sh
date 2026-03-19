#!/usr/bin/env bash
set -euo pipefail

###############################################################################
# Tenon AI - Database QA Runner
#
# Runs the database QA pass using runtime-generated SQL artifacts.
#
# By default this script:
#   1. Loads DB config from tenon-backend/.env
#   2. Uses TENON_DATABASE_URL_SYNC (or TENON_DATABASE_URL fallback)
#   3. Enforces local postgres db "tenon" (localhost/127.0.0.1)
#   4. Applies alembic migrations
#   5. Executes protocol sections in recommended order
#   6. Seeds before write tests and cleans up afterward
#
# Usage:
#   ./qa_verifications/Database-Protocol-QA/run_db_protocol_qa.sh
#   ./qa_verifications/Database-Protocol-QA/run_db_protocol_qa.sh --skip-migrations
#   ./qa_verifications/Database-Protocol-QA/run_db_protocol_qa.sh --skip-cleanup
#   ./qa_verifications/Database-Protocol-QA/run_db_protocol_qa.sh --allow-nonlocal
###############################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="$BACKEND_ROOT/.env"
RESULTS_DIR="$SCRIPT_DIR/db_protocol_qa_latest"
REPORT_MD="$RESULTS_DIR/db_protocol_qa_report.md"
ARTIFACTS_DIR="$RESULTS_DIR/artifacts"
RESULTS_LOGS_DIR="$ARTIFACTS_DIR/logs"
RESULTS_SQL_DIR="$ARTIFACTS_DIR/sql"
NEGATIVE_CHECKS_MD="$ARTIFACTS_DIR/negative-checks.md"
RUN_STARTED_UTC="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
OVERALL_STATUS="PASS"
RUN_MODE="full"
RUN_STARTED_EPOCH="$(date +%s)"
RUN_FINISHED_UTC=""
FAILURE_NOTES=()

SKIP_MIGRATIONS=0
SKIP_CLEANUP=0
ALLOW_NONLOCAL=0

declare -A NEGATIVE_EXPECTED_ERRORS=(
  ["11_section_10_stress_edge"]=1
)

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
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
  --skip-migrations   Skip \`poetry run alembic upgrade head\`
  --skip-cleanup      Skip final cleanup SQL
  --allow-nonlocal    Do not enforce localhost:5432/tenon URL check
  -h, --help          Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-migrations) SKIP_MIGRATIONS=1; RUN_MODE="custom"; shift ;;
    --skip-cleanup) SKIP_CLEANUP=1; RUN_MODE="custom"; shift ;;
    --allow-nonlocal) ALLOW_NONLOCAL=1; RUN_MODE="custom"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) fail "Unknown argument: $1"; usage; exit 1 ;;
  esac
done

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    fail "Required command not found: $1"
    exit 1
  fi
}

record_failure() {
  FAILURE_NOTES+=("$1")
}

init_summary_files() {
  cat >"$REPORT_MD" <<EOF
# Database-Protocol QA Verification

## Run Summary

- Started (UTC): \`$RUN_STARTED_UTC\`
- Finished (UTC): \`pending\`
- Overall status: \`pending\`
- Runner: \`./qa_verifications/Database-Protocol-QA/run_db_protocol_qa.sh\`
- Run mode: \`$RUN_MODE\`
- Database URL: \`$DB_URL\`

## Artifact Layout
- \`artifacts/logs/\`: full command output for each step
- \`artifacts/sql/\`: SQL scripts generated and executed by this run
- \`artifacts/negative-checks.md\`: negative-check evidence (expected vs observed errors)

## Step Results
| Step | Check Type | Status | Duration (s) | Expected Errors | Observed Errors | Log |
|---|---|---|---:|---:|---:|---|
EOF

  cat >"$NEGATIVE_CHECKS_MD" <<'EOF'
# Negative Checks

This file captures negative-check assertions and `ERROR:` lines used for expected-failure tests.
EOF
}

append_summary_row() {
  local step="$1"
  local check_type="$2"
  local status="$3"
  local duration_s="$4"
  local expected_error_count="$5"
  local observed_error_count="$6"
  local log_ref="$7"
  local log_cell="-"

  if [[ "$log_ref" != "-" ]]; then
    local base
    local link_target
    base="$(basename "$log_ref")"
    if [[ "$log_ref" == artifacts/* ]]; then
      link_target="$log_ref"
    else
      link_target="artifacts/$log_ref"
    fi
    log_cell="[$base]($link_target)"
  fi

  printf '| `%s` | `%s` | `%s` | %s | %s | %s | %s |\n' \
    "$step" "$check_type" "$status" "$duration_s" "$expected_error_count" "$observed_error_count" "$log_cell" >>"$REPORT_MD"
}

append_negative_check_details() {
  local step="$1"
  local log_file="$2"
  local expected_error_count="$3"
  local observed_error_count="$4"
  local rel_log="artifacts/logs/$(basename "$log_file")"
  local errors
  errors="$(grep -n 'ERROR:' "$log_file" | sed -E 's|^[0-9]+:psql:.*/(sql/[^:]+):([0-9]+): ERROR: |\1:\2 ERROR: |' || true)"

  if [[ -z "$errors" ]]; then
    return
  fi

  {
    echo ""
    echo "## $step"
    echo ""
    echo "- Expected errors: \`$expected_error_count\`"
    echo "- Observed errors: \`$observed_error_count\`"
    echo ""
    echo "Source log: [$rel_log]($rel_log)"
    echo ""
    echo '```text'
    echo "$errors"
    echo '```'
  } >>"$NEGATIVE_CHECKS_MD"
}

finalize_summary() {
  local finished_utc total_duration_s
  finished_utc="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  RUN_FINISHED_UTC="$finished_utc"
  total_duration_s="$(( $(date +%s) - RUN_STARTED_EPOCH ))"

  # Replace pending summary values with actual run results.
  if [[ -f "$REPORT_MD" ]]; then
    python3 - "$REPORT_MD" "$finished_utc" "$OVERALL_STATUS" <<'PY'
from pathlib import Path
import sys

report = Path(sys.argv[1])
finished = sys.argv[2]
status = sys.argv[3]
content = report.read_text(encoding="utf-8")
content = content.replace("- Finished (UTC): `pending`", f"- Finished (UTC): `{finished}`", 1)
content = content.replace("- Overall status: `pending`", f"- Overall status: `{status}`", 1)
report.write_text(content, encoding="utf-8")
PY
  fi

  {
    echo ""
    echo "## Timing"
    echo ""
    echo "- Total duration (s): \`$total_duration_s\`"
    echo "- Started (UTC): \`$RUN_STARTED_UTC\`"
    echo "- Finished (UTC): \`$finished_utc\`"
    echo "- Per-step durations are listed in the Step Results table."
    echo ""
    echo "## Failures"
    echo ""
    if [[ "${#FAILURE_NOTES[@]}" -eq 0 ]]; then
      echo "- None"
    else
      printf '%s\n' "${FAILURE_NOTES[@]}"
    fi
  } >>"$REPORT_MD"
}

run_cmd_step() {
  local label="$1"
  shift
  local log_file="$RESULTS_LOGS_DIR/${label}.log"
  local start_ts end_ts duration_s rc error_count status

  info "Running ${label}"

  start_ts="$(date +%s)"
  set +e
  "$@" 2>&1 | tee "$log_file"
  rc=${PIPESTATUS[0]}
  set -e
  end_ts="$(date +%s)"

  duration_s=$((end_ts - start_ts))
  error_count="$(grep -c 'ERROR:' "$log_file" || true)"

  if [[ $rc -eq 0 && "$error_count" -eq 0 ]]; then
    status="PASS"
    append_summary_row "$label" "positive" "$status" "$duration_s" "0" "$error_count" "logs/$(basename "$log_file")"
    ok "${label} completed. Log: $log_file"
  else
    status="FAIL"
    OVERALL_STATUS="FAIL"
    append_summary_row "$label" "positive" "$status" "$duration_s" "0" "$error_count" "logs/$(basename "$log_file")"
    record_failure "- Step \`$label\` failed. See \`artifacts/logs/$(basename "$log_file")\`."
    fail "${label} failed. See: $log_file"
    finalize_summary
    exit 1
  fi
}

run_sql_file() {
  local label="$1"
  local sql_file="$2"
  local on_error_stop="$3"
  local expected_error_count="${4:-}"
  local log_file="$RESULTS_LOGS_DIR/${label}.log"
  local start_ts end_ts duration_s rc error_count status

  info "Running ${label} (ON_ERROR_STOP=${on_error_stop})"

  start_ts="$(date +%s)"
  set +e
  psql "$DB_URL" -v ON_ERROR_STOP="$on_error_stop" -f "$sql_file" 2>&1 | tee "$log_file"
  rc=${PIPESTATUS[0]}
  set -e
  end_ts="$(date +%s)"

  duration_s=$((end_ts - start_ts))
  error_count="$(grep -c 'ERROR:' "$log_file" || true)"

  if [[ "$on_error_stop" == "1" ]]; then
    if [[ $rc -eq 0 && "$error_count" -eq 0 ]]; then
      status="PASS"
      append_summary_row "$label" "positive" "$status" "$duration_s" "0" "$error_count" "logs/$(basename "$log_file")"
      ok "${label} completed. Log: $log_file"
    else
      status="FAIL"
      OVERALL_STATUS="FAIL"
      append_summary_row "$label" "positive" "$status" "$duration_s" "0" "$error_count" "logs/$(basename "$log_file")"
      record_failure "- Step \`$label\` failed. See \`artifacts/logs/$(basename "$log_file")\`."
      fail "${label} failed. See: $log_file"
      finalize_summary
      exit 1
    fi
  else
    if [[ -z "$expected_error_count" ]]; then
      OVERALL_STATUS="FAIL"
      append_summary_row "$label" "negative" "FAIL" "$duration_s" "unset" "$error_count" "logs/$(basename "$log_file")"
      record_failure "- Step \`$label\` misconfigured negative-check expectation."
      fail "Negative check misconfigured for ${label}: expected error count not provided."
      finalize_summary
      exit 1
    fi

    append_negative_check_details "$label" "$log_file" "$expected_error_count" "$error_count"

    if [[ $rc -eq 0 && "$error_count" -eq "$expected_error_count" ]]; then
      status="PASS"
      append_summary_row "$label" "negative" "$status" "$duration_s" "$expected_error_count" "$error_count" "logs/$(basename "$log_file")"
      ok "${label} completed. Negative check matched expected errors (${expected_error_count}). Log: $log_file"
    else
      status="FAIL"
      OVERALL_STATUS="FAIL"
      append_summary_row "$label" "negative" "$status" "$duration_s" "$expected_error_count" "$error_count" "logs/$(basename "$log_file")"
      record_failure "- Step \`$label\` failed negative-check assertion (expected $expected_error_count, observed $error_count). See \`artifacts/logs/$(basename "$log_file")\`."
      fail "${label} failed negative-check assertion (expected ${expected_error_count} errors, observed ${error_count}). See: $log_file"
      finalize_summary
      exit 1
    fi
  fi
}

write_runtime_sql_artifacts() {
  RUNTIME_SECTION_1_SQL="$RESULTS_SQL_DIR/01_section_1_schema_verification.sql"
  RUNTIME_SECTION_2_SQL="$RESULTS_SQL_DIR/08_section_2_constraint_enforcement.sql"
  RUNTIME_SECTION_3_SQL="$RESULTS_SQL_DIR/09_section_3_lifecycle.sql"
  RUNTIME_SECTION_4_SQL="$RESULTS_SQL_DIR/02_section_4_referential_integrity.sql"
  RUNTIME_SECTION_5_SQL="$RESULTS_SQL_DIR/03_section_5_enum_status.sql"
  RUNTIME_SECTION_6_SQL="$RESULTS_SQL_DIR/04_section_6_temporal.sql"
  RUNTIME_SECTION_7_SQL="$RESULTS_SQL_DIR/05_section_7_json_validation.sql"
  RUNTIME_SECTION_8_SQL="$RESULTS_SQL_DIR/06_section_8_index_effectiveness.sql"
  RUNTIME_SECTION_9_SQL="$RESULTS_SQL_DIR/07_section_9_migration_safety.sql"
  RUNTIME_SECTION_11_SQL="$RESULTS_SQL_DIR/07b_section_11_full_schema_coverage.sql"
  RUNTIME_SECTION_10_SQL="$RESULTS_SQL_DIR/10_section_10_stress_edge.sql"
  RUNTIME_SEED_SQL="$RESULTS_SQL_DIR/11_seed.sql"
  RUNTIME_CLEANUP_SQL="$RESULTS_SQL_DIR/12_cleanup.sql"

  cat >"$RUNTIME_SECTION_1_SQL" <<'SQL'
-- Section 1: Schema verification (runtime-compatible)
SELECT current_database() AS database_name, current_user AS db_user, now() AS checked_at;

SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
ORDER BY table_name;

SELECT
  c.table_name,
  c.column_name,
  c.data_type,
  c.is_nullable,
  c.column_default
FROM information_schema.columns c
WHERE c.table_schema = 'public'
ORDER BY c.table_name, c.ordinal_position;

SELECT
  tc.table_name,
  tc.constraint_name,
  tc.constraint_type
FROM information_schema.table_constraints tc
WHERE tc.table_schema = 'public'
ORDER BY tc.table_name, tc.constraint_type, tc.constraint_name;

SELECT indexname, tablename, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
SQL

  cat >"$RUNTIME_SECTION_2_SQL" <<'SQL'
-- Section 2: Constraint enforcement (full behavioral coverage)
BEGIN;
SET LOCAL TIME ZONE 'UTC';

DROP TABLE IF EXISTS qa_constraint_enforcement_results;
CREATE TEMP TABLE qa_constraint_enforcement_results (
  category text NOT NULL,
  object_name text NOT NULL,
  check_name text NOT NULL,
  passed boolean NOT NULL,
  details text NOT NULL
);

-- 2.1 NOT NULL: one mutation test per NOT NULL column
DO $$
DECLARE
  rec record;
  v_row_tid text;
  v_state text;
  v_msg text;
BEGIN
  FOR rec IN
    SELECT
      n.nspname AS schema_name,
      t.relname AS table_name,
      a.attname AS column_name
    FROM pg_attribute a
    JOIN pg_class t ON t.oid = a.attrelid
    JOIN pg_namespace n ON n.oid = t.relnamespace
    WHERE n.nspname = 'public'
      AND t.relkind = 'r'
      AND a.attnum > 0
      AND NOT a.attisdropped
      AND a.attnotnull
    ORDER BY n.nspname, t.relname, a.attname
  LOOP
    EXECUTE format('SELECT ctid::text FROM %I.%I LIMIT 1', rec.schema_name, rec.table_name)
      INTO v_row_tid;

    IF v_row_tid IS NULL THEN
      INSERT INTO qa_constraint_enforcement_results
      VALUES (
        'constraint_not_null',
        format('%I.%I.%I', rec.schema_name, rec.table_name, rec.column_name),
        'reject_null_write',
        FALSE,
        'no_row_available_for_mutation_test'
      );
      CONTINUE;
    END IF;

    BEGIN
      EXECUTE format(
        'UPDATE %I.%I SET %I = NULL WHERE ctid = %L::tid',
        rec.schema_name, rec.table_name, rec.column_name, v_row_tid
      );
      INSERT INTO qa_constraint_enforcement_results
      VALUES (
        'constraint_not_null',
        format('%I.%I.%I', rec.schema_name, rec.table_name, rec.column_name),
        'reject_null_write',
        FALSE,
        'mutation_unexpectedly_succeeded'
      );
    EXCEPTION WHEN OTHERS THEN
      GET STACKED DIAGNOSTICS v_state = RETURNED_SQLSTATE, v_msg = MESSAGE_TEXT;
      INSERT INTO qa_constraint_enforcement_results
      VALUES (
        'constraint_not_null',
        format('%I.%I.%I', rec.schema_name, rec.table_name, rec.column_name),
        'reject_null_write',
        v_state = '23502',
        format('sqlstate=%s message=%s', v_state, v_msg)
      );
    END;
  END LOOP;
END $$;

-- 2.2 UNIQUE + PRIMARY KEY: one mutation test per constraint
DO $$
DECLARE
  rec record;
  v_tid_a text;
  v_tid_b text;
  v_non_null_predicate text;
  v_single_non_null_predicate text;
  v_set_expr text;
  v_state text;
  v_msg text;
  v_constraint text;
BEGIN
  FOR rec IN
    SELECT
      c.contype,
      n.nspname AS schema_name,
      t.relname AS table_name,
      c.conname AS constraint_name,
      array_agg(a.attname ORDER BY ord.ordinality) AS columns
    FROM pg_constraint c
    JOIN pg_class t ON t.oid = c.conrelid
    JOIN pg_namespace n ON n.oid = t.relnamespace
    JOIN LATERAL unnest(c.conkey) WITH ORDINALITY AS ord(attnum, ordinality) ON TRUE
    JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ord.attnum
    WHERE n.nspname = 'public'
      AND t.relkind = 'r'
      AND c.contype IN ('p', 'u')
    GROUP BY c.contype, n.nspname, t.relname, c.conname
    ORDER BY n.nspname, t.relname, c.conname
  LOOP
    v_tid_a := NULL;
    v_tid_b := NULL;

    SELECT string_agg(format('a.%I IS NOT NULL AND b.%I IS NOT NULL', col, col), ' AND ')
    INTO v_non_null_predicate
    FROM unnest(rec.columns) AS u(col);

    SELECT string_agg(format('%I IS NOT NULL', col), ' AND ')
    INTO v_single_non_null_predicate
    FROM unnest(rec.columns) AS u(col);

    EXECUTE format(
      'SELECT a.ctid::text, b.ctid::text
       FROM %I.%I a
       JOIN %I.%I b ON a.ctid <> b.ctid
       WHERE %s
       LIMIT 1',
      rec.schema_name, rec.table_name, rec.schema_name, rec.table_name, v_non_null_predicate
    )
      INTO v_tid_a, v_tid_b;

    BEGIN
      IF v_tid_a IS NOT NULL AND v_tid_b IS NOT NULL THEN
        SELECT string_agg(
                 format('%I = (SELECT %I FROM %I.%I WHERE ctid = %L::tid)', col, col, rec.schema_name, rec.table_name, v_tid_b),
                 ', '
               )
        INTO v_set_expr
        FROM unnest(rec.columns) AS u(col);

        EXECUTE format(
          'UPDATE %I.%I SET %s WHERE ctid = %L::tid',
          rec.schema_name, rec.table_name, v_set_expr, v_tid_a
        );
      ELSE
        EXECUTE format(
          'SELECT ctid::text FROM %I.%I WHERE %s LIMIT 1',
          rec.schema_name, rec.table_name, v_single_non_null_predicate
        ) INTO v_tid_a;
        IF v_tid_a IS NULL THEN
          INSERT INTO qa_constraint_enforcement_results
          VALUES (
            CASE WHEN rec.contype = 'p' THEN 'constraint_primary_key' ELSE 'constraint_unique' END,
            format('%I.%I.%I', rec.schema_name, rec.table_name, rec.constraint_name),
            'reject_duplicate_write',
            FALSE,
            'no_row_available_for_mutation_test'
          );
          CONTINUE;
        END IF;
        EXECUTE format(
          'INSERT INTO %I.%I SELECT * FROM %I.%I WHERE ctid = %L::tid',
          rec.schema_name, rec.table_name, rec.schema_name, rec.table_name, v_tid_a
        );
      END IF;

      INSERT INTO qa_constraint_enforcement_results
      VALUES (
        CASE WHEN rec.contype = 'p' THEN 'constraint_primary_key' ELSE 'constraint_unique' END,
        format('%I.%I.%I', rec.schema_name, rec.table_name, rec.constraint_name),
        'reject_duplicate_write',
        FALSE,
        'duplicate_mutation_unexpectedly_succeeded'
      );
    EXCEPTION WHEN OTHERS THEN
      GET STACKED DIAGNOSTICS
        v_state = RETURNED_SQLSTATE,
        v_msg = MESSAGE_TEXT,
        v_constraint = CONSTRAINT_NAME;
      INSERT INTO qa_constraint_enforcement_results
      VALUES (
        CASE WHEN rec.contype = 'p' THEN 'constraint_primary_key' ELSE 'constraint_unique' END,
        format('%I.%I.%I', rec.schema_name, rec.table_name, rec.constraint_name),
        'reject_duplicate_write',
        v_state = '23505' AND v_constraint = rec.constraint_name,
        format('sqlstate=%s constraint=%s message=%s', v_state, COALESCE(v_constraint, 'NULL'), v_msg)
      );
    END;
  END LOOP;
END $$;

-- 2.3 CHECK: one mutation test per check constraint
DO $$
DECLARE
  rec record;
  v_sql text;
  v_state text;
  v_msg text;
  v_constraint text;
BEGIN
  FOR rec IN
    SELECT
      n.nspname AS schema_name,
      t.relname AS table_name,
      c.conname AS constraint_name
    FROM pg_constraint c
    JOIN pg_class t ON t.oid = c.conrelid
    JOIN pg_namespace n ON n.oid = t.relnamespace
    WHERE n.nspname = 'public'
      AND t.relkind = 'r'
      AND c.contype = 'c'
    ORDER BY n.nspname, t.relname, c.conname
  LOOP
    v_sql := NULL;

    CASE rec.constraint_name
      WHEN 'ck_candidate_day_audits_day_index' THEN
        v_sql := 'UPDATE candidate_day_audits SET day_index = 1 WHERE id = 970001';
      WHEN 'ck_evaluation_day_scores_day_index' THEN
        v_sql := 'UPDATE evaluation_day_scores SET day_index = 6 WHERE id = 970011';
      WHEN 'ck_evaluation_runs_completed_after_started' THEN
        v_sql := 'UPDATE evaluation_runs SET completed_at = started_at - INTERVAL ''1 second'' WHERE id = 970001';
      WHEN 'ck_evaluation_runs_recommendation' THEN
        v_sql := 'UPDATE evaluation_runs SET recommendation = ''__invalid__'' WHERE id = 970001';
      WHEN 'ck_evaluation_runs_status' THEN
        v_sql := 'UPDATE evaluation_runs SET status = ''__invalid__'' WHERE id = 970001';
      WHEN 'ck_precommit_bundle_content_source' THEN
        v_sql := 'UPDATE precommit_bundles SET patch_text = NULL, storage_ref = NULL WHERE id = 970001';
      WHEN 'ck_precommit_bundles_status' THEN
        v_sql := 'UPDATE precommit_bundles SET status = ''__invalid__'' WHERE id = 970001';
      WHEN 'ck_recording_assets_status' THEN
        v_sql := 'UPDATE recording_assets SET status = ''__invalid__'' WHERE id = 970001';
      WHEN 'ck_scenario_versions_status' THEN
        v_sql := 'UPDATE scenario_versions SET status = ''__invalid__'' WHERE id = 970001';
      WHEN 'ck_simulations_status_lifecycle' THEN
        v_sql := 'UPDATE simulations SET status = ''__invalid__'' WHERE id = 970001';
      WHEN 'ck_transcripts_status' THEN
        v_sql := 'UPDATE transcripts SET status = ''__invalid__'' WHERE id = 970001';
    END CASE;

    IF v_sql IS NULL THEN
      INSERT INTO qa_constraint_enforcement_results
      VALUES (
        'constraint_check',
        format('%I.%I.%I', rec.schema_name, rec.table_name, rec.constraint_name),
        'reject_check_violation',
        FALSE,
        'no_mutation_case_defined_for_check_constraint'
      );
      CONTINUE;
    END IF;

    BEGIN
      EXECUTE v_sql;
      INSERT INTO qa_constraint_enforcement_results
      VALUES (
        'constraint_check',
        format('%I.%I.%I', rec.schema_name, rec.table_name, rec.constraint_name),
        'reject_check_violation',
        FALSE,
        'check_violation_mutation_unexpectedly_succeeded'
      );
    EXCEPTION WHEN OTHERS THEN
      GET STACKED DIAGNOSTICS
        v_state = RETURNED_SQLSTATE,
        v_msg = MESSAGE_TEXT,
        v_constraint = CONSTRAINT_NAME;
      INSERT INTO qa_constraint_enforcement_results
      VALUES (
        'constraint_check',
        format('%I.%I.%I', rec.schema_name, rec.table_name, rec.constraint_name),
        'reject_check_violation',
        v_state = '23514' AND v_constraint = rec.constraint_name,
        format('sqlstate=%s constraint=%s message=%s', v_state, COALESCE(v_constraint, 'NULL'), v_msg)
      );
    END;
  END LOOP;
END $$;

-- 2.4 FOREIGN KEY: one invalid-reference mutation test per FK
DO $$
DECLARE
  rec record;
  v_row_tid text;
  v_predicate text;
  v_set_expr text;
  v_value_expr text;
  v_type text;
  v_state text;
  v_msg text;
  v_constraint text;
  v_i integer;
BEGIN
  FOR rec IN
    SELECT
      c.conname AS constraint_name,
      child_ns.nspname AS child_schema,
      child.relname AS child_table,
      array_agg(ca.attname ORDER BY ck.ordinality) AS child_columns,
      array_agg(format_type(ca.atttypid, ca.atttypmod) ORDER BY ck.ordinality) AS child_types
    FROM pg_constraint c
    JOIN pg_class child ON child.oid = c.conrelid
    JOIN pg_namespace child_ns ON child_ns.oid = child.relnamespace
    JOIN LATERAL unnest(c.conkey) WITH ORDINALITY AS ck(attnum, ordinality) ON TRUE
    JOIN pg_attribute ca ON ca.attrelid = child.oid AND ca.attnum = ck.attnum
    WHERE child_ns.nspname = 'public'
      AND c.contype = 'f'
    GROUP BY c.conname, child_ns.nspname, child.relname
    ORDER BY child_ns.nspname, child.relname, c.conname
  LOOP
    SELECT string_agg(format('%I IS NOT NULL', col), ' AND ')
    INTO v_predicate
    FROM unnest(rec.child_columns) AS u(col);

    EXECUTE format(
      'SELECT ctid::text FROM %I.%I WHERE %s LIMIT 1',
      rec.child_schema, rec.child_table, v_predicate
    ) INTO v_row_tid;

    IF v_row_tid IS NULL THEN
      INSERT INTO qa_constraint_enforcement_results
      VALUES (
        'constraint_fk_reference',
        format('%I.%I.%I', rec.child_schema, rec.child_table, rec.constraint_name),
        'reject_invalid_reference',
        FALSE,
        'no_child_row_with_non_null_fk_for_mutation_test'
      );
      CONTINUE;
    END IF;

    v_set_expr := '';
    FOR v_i IN 1..array_length(rec.child_columns, 1) LOOP
      v_type := rec.child_types[v_i];
      IF v_type IN ('smallint', 'integer', 'bigint') THEN
        v_value_expr := format('(-900000 - %s)::%s', v_i, v_type);
      ELSIF v_type IN ('numeric', 'decimal') OR v_type LIKE 'numeric(%' THEN
        v_value_expr := format('(-900000 - %s)::numeric', v_i);
      ELSIF v_type = 'uuid' THEN
        v_value_expr := format('%L::uuid', '00000000-0000-0000-0000-000000000000');
      ELSIF v_type = 'text' OR v_type LIKE 'character varying%' THEN
        v_value_expr := format('%L::%s', '__qa_missing_fk__', v_type);
      ELSE
        INSERT INTO qa_constraint_enforcement_results
        VALUES (
          'constraint_fk_reference',
          format('%I.%I.%I', rec.child_schema, rec.child_table, rec.constraint_name),
          'reject_invalid_reference',
          FALSE,
          format('unsupported_fk_column_type=%s column=%s', v_type, rec.child_columns[v_i])
        );
        v_set_expr := NULL;
        EXIT;
      END IF;

      v_set_expr := v_set_expr ||
        CASE WHEN v_i > 1 THEN ', ' ELSE '' END ||
        format('%I = %s', rec.child_columns[v_i], v_value_expr);
    END LOOP;

    IF v_set_expr IS NULL THEN
      CONTINUE;
    END IF;

    BEGIN
      EXECUTE format(
        'UPDATE %I.%I SET %s WHERE ctid = %L::tid',
        rec.child_schema, rec.child_table, v_set_expr, v_row_tid
      );
      INSERT INTO qa_constraint_enforcement_results
      VALUES (
        'constraint_fk_reference',
        format('%I.%I.%I', rec.child_schema, rec.child_table, rec.constraint_name),
        'reject_invalid_reference',
        FALSE,
        'fk_violation_mutation_unexpectedly_succeeded'
      );
    EXCEPTION WHEN OTHERS THEN
      GET STACKED DIAGNOSTICS
        v_state = RETURNED_SQLSTATE,
        v_msg = MESSAGE_TEXT,
        v_constraint = CONSTRAINT_NAME;
      INSERT INTO qa_constraint_enforcement_results
      VALUES (
        'constraint_fk_reference',
        format('%I.%I.%I', rec.child_schema, rec.child_table, rec.constraint_name),
        'reject_invalid_reference',
        v_state = '23503' AND v_constraint = rec.constraint_name,
        format('sqlstate=%s constraint=%s message=%s', v_state, COALESCE(v_constraint, 'NULL'), v_msg)
      );
    END;
  END LOOP;
END $$;

-- 2.5 FOREIGN KEY delete behavior: one action test per FK
DO $$
DECLARE
  rec record;
  v_idx integer := 0;
  v_parent_table text;
  v_child_table text;
  v_constraint_name text;
  v_action text;
  v_count integer;
  v_state text;
  v_msg text;
BEGIN
  FOR rec IN
    SELECT
      c.conname AS constraint_name,
      c.confdeltype
    FROM pg_constraint c
    JOIN pg_class child ON child.oid = c.conrelid
    JOIN pg_namespace child_ns ON child_ns.oid = child.relnamespace
    WHERE child_ns.nspname = 'public'
      AND c.contype = 'f'
    ORDER BY c.conname
  LOOP
    v_idx := v_idx + 1;
    v_parent_table := format('qa_fk_parent_%s', v_idx);
    v_child_table := format('qa_fk_child_%s', v_idx);
    v_constraint_name := format('qa_fk_behavior_%s', v_idx);

    v_action := CASE rec.confdeltype
      WHEN 'a' THEN 'NO ACTION'
      WHEN 'r' THEN 'RESTRICT'
      WHEN 'c' THEN 'CASCADE'
      WHEN 'n' THEN 'SET NULL'
      WHEN 'd' THEN 'SET DEFAULT'
      ELSE 'UNKNOWN'
    END;

    EXECUTE format('CREATE TEMP TABLE %I (id integer PRIMARY KEY) ON COMMIT DROP', v_parent_table);

    IF v_action = 'SET DEFAULT' THEN
      EXECUTE format(
        'CREATE TEMP TABLE %I (id integer PRIMARY KEY, parent_id integer NOT NULL DEFAULT 0) ON COMMIT DROP',
        v_child_table
      );
      EXECUTE format('INSERT INTO %I (id) VALUES (0)', v_parent_table);
    ELSE
      EXECUTE format(
        'CREATE TEMP TABLE %I (id integer PRIMARY KEY, parent_id integer NOT NULL) ON COMMIT DROP',
        v_child_table
      );
    END IF;

    EXECUTE format(
      'ALTER TABLE %I ADD CONSTRAINT %I FOREIGN KEY (parent_id) REFERENCES %I(id) ON DELETE %s',
      v_child_table, v_constraint_name, v_parent_table, v_action
    );

    EXECUTE format('INSERT INTO %I (id) VALUES (1)', v_parent_table);
    EXECUTE format('INSERT INTO %I (id, parent_id) VALUES (1, 1)', v_child_table);

    IF v_action IN ('NO ACTION', 'RESTRICT') THEN
      BEGIN
        EXECUTE format('DELETE FROM %I WHERE id = 1', v_parent_table);
        INSERT INTO qa_constraint_enforcement_results
        VALUES (
          'constraint_fk_delete_action',
          rec.constraint_name,
          'on_delete_behavior',
          FALSE,
          format('expected_delete_block_for_%s_but_delete_succeeded', v_action)
        );
      EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS v_state = RETURNED_SQLSTATE, v_msg = MESSAGE_TEXT;
        INSERT INTO qa_constraint_enforcement_results
        VALUES (
          'constraint_fk_delete_action',
          rec.constraint_name,
          'on_delete_behavior',
          v_state = '23503',
          format('action=%s sqlstate=%s message=%s', v_action, v_state, v_msg)
        );
      END;
    ELSIF v_action = 'CASCADE' THEN
      EXECUTE format('DELETE FROM %I WHERE id = 1', v_parent_table);
      EXECUTE format('SELECT COUNT(*) FROM %I WHERE parent_id = 1', v_child_table) INTO v_count;
      INSERT INTO qa_constraint_enforcement_results
      VALUES (
        'constraint_fk_delete_action',
        rec.constraint_name,
        'on_delete_behavior',
        v_count = 0,
        format('action=%s remaining_child_rows=%s', v_action, v_count)
      );
    ELSIF v_action = 'SET NULL' THEN
      EXECUTE format('DELETE FROM %I WHERE id = 1', v_parent_table);
      EXECUTE format('SELECT COUNT(*) FROM %I WHERE id = 1 AND parent_id IS NULL', v_child_table) INTO v_count;
      INSERT INTO qa_constraint_enforcement_results
      VALUES (
        'constraint_fk_delete_action',
        rec.constraint_name,
        'on_delete_behavior',
        v_count = 1,
        format('action=%s nullified_rows=%s', v_action, v_count)
      );
    ELSIF v_action = 'SET DEFAULT' THEN
      EXECUTE format('DELETE FROM %I WHERE id = 1', v_parent_table);
      EXECUTE format('SELECT COUNT(*) FROM %I WHERE id = 1 AND parent_id = 0', v_child_table) INTO v_count;
      INSERT INTO qa_constraint_enforcement_results
      VALUES (
        'constraint_fk_delete_action',
        rec.constraint_name,
        'on_delete_behavior',
        v_count = 1,
        format('action=%s defaulted_rows=%s', v_action, v_count)
      );
    ELSE
      INSERT INTO qa_constraint_enforcement_results
      VALUES (
        'constraint_fk_delete_action',
        rec.constraint_name,
        'on_delete_behavior',
        FALSE,
        format('unsupported_confdeltype=%s', rec.confdeltype)
      );
    END IF;
  END LOOP;
END $$;

-- 2.6 FOREIGN KEY update behavior: one action test per FK
DO $$
DECLARE
  rec record;
  v_idx integer := 0;
  v_parent_table text;
  v_child_table text;
  v_constraint_name text;
  v_action text;
  v_count integer;
  v_state text;
  v_msg text;
BEGIN
  FOR rec IN
    SELECT
      c.conname AS constraint_name,
      c.confupdtype
    FROM pg_constraint c
    JOIN pg_class child ON child.oid = c.conrelid
    JOIN pg_namespace child_ns ON child_ns.oid = child.relnamespace
    WHERE child_ns.nspname = 'public'
      AND c.contype = 'f'
    ORDER BY c.conname
  LOOP
    v_idx := v_idx + 1;
    v_parent_table := format('qa_fk_update_parent_%s', v_idx);
    v_child_table := format('qa_fk_update_child_%s', v_idx);
    v_constraint_name := format('qa_fk_update_behavior_%s', v_idx);

    v_action := CASE rec.confupdtype
      WHEN 'a' THEN 'NO ACTION'
      WHEN 'r' THEN 'RESTRICT'
      WHEN 'c' THEN 'CASCADE'
      WHEN 'n' THEN 'SET NULL'
      WHEN 'd' THEN 'SET DEFAULT'
      ELSE 'UNKNOWN'
    END;

    EXECUTE format('CREATE TEMP TABLE %I (id integer PRIMARY KEY) ON COMMIT DROP', v_parent_table);

    IF v_action = 'SET DEFAULT' THEN
      EXECUTE format(
        'CREATE TEMP TABLE %I (id integer PRIMARY KEY, parent_id integer NOT NULL DEFAULT 0) ON COMMIT DROP',
        v_child_table
      );
      EXECUTE format('INSERT INTO %I (id) VALUES (0)', v_parent_table);
    ELSIF v_action = 'SET NULL' THEN
      EXECUTE format(
        'CREATE TEMP TABLE %I (id integer PRIMARY KEY, parent_id integer) ON COMMIT DROP',
        v_child_table
      );
    ELSE
      EXECUTE format(
        'CREATE TEMP TABLE %I (id integer PRIMARY KEY, parent_id integer NOT NULL) ON COMMIT DROP',
        v_child_table
      );
    END IF;

    EXECUTE format(
      'ALTER TABLE %I ADD CONSTRAINT %I FOREIGN KEY (parent_id) REFERENCES %I(id) ON UPDATE %s',
      v_child_table, v_constraint_name, v_parent_table, v_action
    );

    EXECUTE format('INSERT INTO %I (id) VALUES (1)', v_parent_table);
    EXECUTE format('INSERT INTO %I (id, parent_id) VALUES (1, 1)', v_child_table);

    IF v_action IN ('NO ACTION', 'RESTRICT') THEN
      BEGIN
        EXECUTE format('UPDATE %I SET id = 2 WHERE id = 1', v_parent_table);
        INSERT INTO qa_constraint_enforcement_results
        VALUES (
          'constraint_fk_update_action',
          rec.constraint_name,
          'on_update_behavior',
          FALSE,
          format('expected_update_block_for_%s_but_update_succeeded', v_action)
        );
      EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS v_state = RETURNED_SQLSTATE, v_msg = MESSAGE_TEXT;
        INSERT INTO qa_constraint_enforcement_results
        VALUES (
          'constraint_fk_update_action',
          rec.constraint_name,
          'on_update_behavior',
          v_state = '23503',
          format('action=%s sqlstate=%s message=%s', v_action, v_state, v_msg)
        );
      END;
    ELSIF v_action = 'CASCADE' THEN
      EXECUTE format('UPDATE %I SET id = 2 WHERE id = 1', v_parent_table);
      EXECUTE format('SELECT COUNT(*) FROM %I WHERE id = 1 AND parent_id = 2', v_child_table) INTO v_count;
      INSERT INTO qa_constraint_enforcement_results
      VALUES (
        'constraint_fk_update_action',
        rec.constraint_name,
        'on_update_behavior',
        v_count = 1,
        format('action=%s cascaded_rows=%s', v_action, v_count)
      );
    ELSIF v_action = 'SET NULL' THEN
      EXECUTE format('UPDATE %I SET id = 2 WHERE id = 1', v_parent_table);
      EXECUTE format('SELECT COUNT(*) FROM %I WHERE id = 1 AND parent_id IS NULL', v_child_table) INTO v_count;
      INSERT INTO qa_constraint_enforcement_results
      VALUES (
        'constraint_fk_update_action',
        rec.constraint_name,
        'on_update_behavior',
        v_count = 1,
        format('action=%s nullified_rows=%s', v_action, v_count)
      );
    ELSIF v_action = 'SET DEFAULT' THEN
      EXECUTE format('UPDATE %I SET id = 2 WHERE id = 1', v_parent_table);
      EXECUTE format('SELECT COUNT(*) FROM %I WHERE id = 1 AND parent_id = 0', v_child_table) INTO v_count;
      INSERT INTO qa_constraint_enforcement_results
      VALUES (
        'constraint_fk_update_action',
        rec.constraint_name,
        'on_update_behavior',
        v_count = 1,
        format('action=%s defaulted_rows=%s', v_action, v_count)
      );
    ELSE
      INSERT INTO qa_constraint_enforcement_results
      VALUES (
        'constraint_fk_update_action',
        rec.constraint_name,
        'on_update_behavior',
        FALSE,
        format('unsupported_confupdtype=%s', rec.confupdtype)
      );
    END IF;
  END LOOP;
END $$;

-- 2.7 Coverage completeness assertions (fail if any discovered object was not tested)
DO $$
DECLARE
  expected_not_null integer;
  expected_pk integer;
  expected_unique integer;
  expected_check integer;
  expected_fk integer;
  actual_not_null integer;
  actual_pk integer;
  actual_unique integer;
  actual_check integer;
  actual_fk_ref integer;
  actual_fk_del integer;
  actual_fk_upd integer;
BEGIN
  SELECT COUNT(*)
  INTO expected_not_null
  FROM pg_attribute a
  JOIN pg_class t ON t.oid = a.attrelid
  JOIN pg_namespace n ON n.oid = t.relnamespace
  WHERE n.nspname = 'public'
    AND t.relkind = 'r'
    AND a.attnum > 0
    AND NOT a.attisdropped
    AND a.attnotnull;

  SELECT COUNT(*)
  INTO expected_pk
  FROM pg_constraint c
  JOIN pg_class t ON t.oid = c.conrelid
  JOIN pg_namespace n ON n.oid = t.relnamespace
  WHERE n.nspname = 'public' AND t.relkind = 'r' AND c.contype = 'p';

  SELECT COUNT(*)
  INTO expected_unique
  FROM pg_constraint c
  JOIN pg_class t ON t.oid = c.conrelid
  JOIN pg_namespace n ON n.oid = t.relnamespace
  WHERE n.nspname = 'public' AND t.relkind = 'r' AND c.contype = 'u';

  SELECT COUNT(*)
  INTO expected_check
  FROM pg_constraint c
  JOIN pg_class t ON t.oid = c.conrelid
  JOIN pg_namespace n ON n.oid = t.relnamespace
  WHERE n.nspname = 'public' AND t.relkind = 'r' AND c.contype = 'c';

  SELECT COUNT(*)
  INTO expected_fk
  FROM pg_constraint c
  JOIN pg_class t ON t.oid = c.conrelid
  JOIN pg_namespace n ON n.oid = t.relnamespace
  WHERE n.nspname = 'public' AND t.relkind = 'r' AND c.contype = 'f';

  SELECT COUNT(*) INTO actual_not_null FROM qa_constraint_enforcement_results WHERE category = 'constraint_not_null';
  SELECT COUNT(*) INTO actual_pk FROM qa_constraint_enforcement_results WHERE category = 'constraint_primary_key';
  SELECT COUNT(*) INTO actual_unique FROM qa_constraint_enforcement_results WHERE category = 'constraint_unique';
  SELECT COUNT(*) INTO actual_check FROM qa_constraint_enforcement_results WHERE category = 'constraint_check';
  SELECT COUNT(*) INTO actual_fk_ref FROM qa_constraint_enforcement_results WHERE category = 'constraint_fk_reference';
  SELECT COUNT(*) INTO actual_fk_del FROM qa_constraint_enforcement_results WHERE category = 'constraint_fk_delete_action';
  SELECT COUNT(*) INTO actual_fk_upd FROM qa_constraint_enforcement_results WHERE category = 'constraint_fk_update_action';

  INSERT INTO qa_constraint_enforcement_results
  VALUES (
    'coverage',
    'constraint_not_null',
    'all_not_null_constraints_tested',
    actual_not_null = expected_not_null,
    format('expected=%s actual=%s', expected_not_null, actual_not_null)
  );

  INSERT INTO qa_constraint_enforcement_results
  VALUES (
    'coverage',
    'constraint_primary_key',
    'all_primary_key_constraints_tested',
    actual_pk = expected_pk,
    format('expected=%s actual=%s', expected_pk, actual_pk)
  );

  INSERT INTO qa_constraint_enforcement_results
  VALUES (
    'coverage',
    'constraint_unique',
    'all_unique_constraints_tested',
    actual_unique = expected_unique,
    format('expected=%s actual=%s', expected_unique, actual_unique)
  );

  INSERT INTO qa_constraint_enforcement_results
  VALUES (
    'coverage',
    'constraint_check',
    'all_check_constraints_tested',
    actual_check = expected_check,
    format('expected=%s actual=%s', expected_check, actual_check)
  );

  INSERT INTO qa_constraint_enforcement_results
  VALUES (
    'coverage',
    'constraint_fk_reference',
    'all_foreign_keys_reference_tested',
    actual_fk_ref = expected_fk,
    format('expected=%s actual=%s', expected_fk, actual_fk_ref)
  );

  INSERT INTO qa_constraint_enforcement_results
  VALUES (
    'coverage',
    'constraint_fk_delete_action',
    'all_foreign_keys_delete_action_tested',
    actual_fk_del = expected_fk,
    format('expected=%s actual=%s', expected_fk, actual_fk_del)
  );

  INSERT INTO qa_constraint_enforcement_results
  VALUES (
    'coverage',
    'constraint_fk_update_action',
    'all_foreign_keys_update_action_tested',
    actual_fk_upd = expected_fk,
    format('expected=%s actual=%s', expected_fk, actual_fk_upd)
  );
END $$;

SELECT
  category,
  COUNT(*) AS total_checks,
  COUNT(*) FILTER (WHERE passed) AS passed_checks,
  COUNT(*) FILTER (WHERE NOT passed) AS failed_checks
FROM qa_constraint_enforcement_results
GROUP BY category
ORDER BY category;

SELECT *
FROM qa_constraint_enforcement_results
WHERE NOT passed
ORDER BY category, object_name, check_name;

DO $$
DECLARE
  v_failures integer;
BEGIN
  SELECT COUNT(*) INTO v_failures
  FROM qa_constraint_enforcement_results
  WHERE NOT passed;

  IF v_failures > 0 THEN
    RAISE EXCEPTION 'Constraint enforcement suite failed with % failing checks', v_failures;
  END IF;
END $$;

ROLLBACK;
SQL

  cat >"$RUNTIME_SECTION_3_SQL" <<'SQL'
-- Section 3: Data mutation lifecycle test (runtime-compatible)
BEGIN;

INSERT INTO companies (id, name, created_at)
VALUES (980001, 'qa_lifecycle_company_runtime', NOW());

INSERT INTO users (id, name, email, role, company_id, password_hash, created_at)
VALUES
  (980001, 'Runtime Recruiter', 'runtime.recruiter@tenon.test', 'recruiter', 980001, NULL, NOW()),
  (980002, 'Runtime Candidate', 'runtime.candidate@tenon.test', 'candidate', NULL, NULL, NOW());

INSERT INTO simulations (
  id, company_id, title, role, tech_stack, seniority, scenario_template,
  created_by, status, created_at, focus, template_key, generating_at,
  ready_for_review_at, activated_at, terminated_at, company_context,
  ai_notice_version, ai_notice_text, ai_eval_enabled_by_day, terminated_reason,
  terminated_by_recruiter_id, day_window_start_local, day_window_end_local,
  day_window_overrides_enabled, day_window_overrides_json
)
VALUES (
  980001, 980001, 'Runtime Lifecycle Simulation', 'Backend Engineer', 'Python,FastAPI,PostgreSQL',
  'senior', 'default-5day-node-postgres', 980001, 'active_inviting', NOW() - INTERVAL '5 days',
  'Runtime QA flow', 'python-fastapi', NOW() - INTERVAL '5 days', NOW() - INTERVAL '4 days',
  NOW() - INTERVAL '3 days', NULL, '{"domain":"qa"}'::json, 'v1', 'AI notice runtime',
  '{"1":true,"2":true,"3":true,"4":true,"5":true}'::json, NULL, NULL, '09:00:00', '17:00:00',
  FALSE, NULL
);

INSERT INTO scenario_versions (
  id, simulation_id, version_index, status, storyline_md, task_prompts_json, rubric_json,
  focus_notes, template_key, tech_stack, seniority, model_name, model_version,
  prompt_version, rubric_version, locked_at, created_at
)
VALUES (
  980001, 980001, 1, 'locked', '# Runtime Scenario', '[]'::json, '{}'::json,
  'runtime focus', 'python-fastapi', 'Python,FastAPI,PostgreSQL', 'senior',
  'gpt-5.4', '2026-03-18', 'sim-v1', 'rubric-v1', NOW() - INTERVAL '3 days', NOW() - INTERVAL '5 days'
);

INSERT INTO tasks (id, simulation_id, day_index, type, title, description, starter_code_path, test_file_path, max_score, template_repo)
VALUES
  (980001, 980001, 1, 'design', 'Day 1', 'Design task', NULL, NULL, 20, 'tenon-hire-dev/tenon-template-python-fastapi'),
  (980002, 980001, 2, 'code', 'Day 2', 'Code task', 'app/main.py', 'tests/test_main.py', 20, 'tenon-hire-dev/tenon-template-python-fastapi'),
  (980003, 980001, 3, 'debug', 'Day 3', 'Debug task', 'app/service.py', 'tests/test_service.py', 20, 'tenon-hire-dev/tenon-template-python-fastapi'),
  (980004, 980001, 4, 'handoff', 'Day 4', 'Demo task', NULL, NULL, 20, 'tenon-hire-dev/tenon-template-python-fastapi'),
  (980005, 980001, 5, 'documentation', 'Day 5', 'Essay task', NULL, NULL, 20, 'tenon-hire-dev/tenon-template-python-fastapi');

INSERT INTO candidate_sessions (
  id, simulation_id, candidate_user_id, invite_email, token, status, started_at, completed_at,
  candidate_name, expires_at, candidate_email, candidate_auth0_sub, claimed_at, invite_email_status,
  invite_email_error, invite_email_last_attempt_at, invite_email_sent_at, candidate_auth0_email,
  scheduled_start_at, candidate_timezone, schedule_locked_at, invite_email_verified_at, day_windows_json, github_username
)
VALUES (
  980001, 980001, 980002, 'runtime.candidate@tenon.test', 'runtime_token_980001', 'completed',
  NOW() - INTERVAL '5 days', NOW() - INTERVAL '1 day', 'Runtime Candidate', NOW() + INTERVAL '7 days',
  'runtime.candidate@tenon.test', 'auth0|runtime-candidate', NOW() - INTERVAL '5 days', 'sent',
  NULL, NOW() - INTERVAL '6 days', NOW() - INTERVAL '6 days', 'runtime.candidate@tenon.test',
  NOW() - INTERVAL '5 days', 'America/New_York', NOW() - INTERVAL '5 days', NOW() - INTERVAL '5 days',
  '[{"dayIndex":1,"windowStartAt":"2026-03-10T14:00:00Z","windowEndAt":"2026-03-10T22:00:00Z"}]'::json, 'runtime-candidate-gh'
);

INSERT INTO submissions (
  id, candidate_session_id, task_id, submitted_at, content_text, code_repo_path,
  tests_passed, tests_failed, test_output, last_run_at, commit_sha, workflow_run_id, diff_summary_json, content_json
)
VALUES
  (980001, 980001, 980001, NOW() - INTERVAL '5 days', 'Day1 submission', NULL, NULL, NULL, NULL, NOW() - INTERVAL '5 days', NULL, NULL, NULL, '{"day":1}'::json),
  (980002, 980001, 980002, NOW() - INTERVAL '4 days', 'Day2 submission', 'repo/path', 12, 0, 'ok', NOW() - INTERVAL '4 days', 'sha2', 'wf2', '{"files":3}', '{"day":2}'::json),
  (980003, 980001, 980003, NOW() - INTERVAL '3 days', 'Day3 submission', 'repo/path', 10, 1, 'minor fail', NOW() - INTERVAL '3 days', 'sha3', 'wf3', '{"files":5}', '{"day":3}'::json),
  (980004, 980001, 980004, NOW() - INTERVAL '2 days', 'Day4 submission', NULL, NULL, NULL, NULL, NOW() - INTERVAL '2 days', NULL, NULL, NULL, '{"day":4}'::json),
  (980005, 980001, 980005, NOW() - INTERVAL '1 day', 'Day5 submission', NULL, NULL, NULL, NULL, NOW() - INTERVAL '1 day', NULL, NULL, NULL, '{"day":5}'::json);

INSERT INTO evaluation_runs (
  id, candidate_session_id, scenario_version_id, status, started_at, completed_at, model_name,
  model_version, prompt_version, rubric_version, job_id, basis_fingerprint, overall_fit_score,
  recommendation, confidence, generated_at, raw_report_json, error_code, metadata_json,
  day2_checkpoint_sha, day3_final_sha, cutoff_commit_sha, transcript_reference
)
VALUES (
  980001, 980001, 980001, 'completed', NOW() - INTERVAL '20 hours', NOW() - INTERVAL '19 hours',
  'gpt-5.4', '2026-03-18', 'eval-v2', 'rubric-v2', '98000300-0000-0000-0000-000000000001',
  'basis_fp_980001', 88.2, 'strong_hire', 0.92, NOW() - INTERVAL '19 hours',
  '{"summary":"runtime-strong"}'::json, NULL, '{"source":"runtime-lifecycle"}'::json,
  'd2cp', 'd3fin', 'cutoff', 'transcript:runtime'
);

INSERT INTO evaluation_day_scores (id, run_id, day_index, score, rubric_results_json, evidence_pointers_json, created_at)
VALUES
  (980011, 980001, 1, 82.0, '{}'::json, '[]'::json, NOW()),
  (980012, 980001, 2, 87.0, '{}'::json, '[]'::json, NOW()),
  (980013, 980001, 3, 90.0, '{}'::json, '[]'::json, NOW()),
  (980014, 980001, 4, 86.0, '{}'::json, '[]'::json, NOW()),
  (980015, 980001, 5, 89.0, '{}'::json, '[]'::json, NOW());

INSERT INTO fit_profiles (id, candidate_session_id, generated_at)
VALUES (980001, 980001, NOW());

SELECT
  c.name AS company_name,
  ru.email AS recruiter_email,
  s.title AS simulation_title,
  cs.invite_email AS candidate_email,
  COUNT(DISTINCT t.id) AS task_count,
  COUNT(DISTINCT sub.id) AS submission_count,
  er.overall_fit_score,
  fp.id AS fit_profile_id
FROM simulations s
JOIN companies c ON c.id = s.company_id
JOIN users ru ON ru.id = s.created_by
JOIN candidate_sessions cs ON cs.simulation_id = s.id
LEFT JOIN tasks t ON t.simulation_id = s.id
LEFT JOIN submissions sub ON sub.candidate_session_id = cs.id
LEFT JOIN evaluation_runs er ON er.candidate_session_id = cs.id
LEFT JOIN fit_profiles fp ON fp.candidate_session_id = cs.id
WHERE s.id = 980001
GROUP BY c.name, ru.email, s.title, cs.invite_email, er.overall_fit_score, fp.id;

ROLLBACK;
SQL

  cat >"$RUNTIME_SECTION_4_SQL" <<'SQL'
-- Section 4: Referential integrity checks (runtime-compatible)
SELECT cda.id FROM candidate_day_audits cda LEFT JOIN candidate_sessions cs ON cda.candidate_session_id = cs.id WHERE cs.id IS NULL;
SELECT cs.id FROM candidate_sessions cs LEFT JOIN simulations s ON cs.simulation_id = s.id WHERE cs.simulation_id IS NOT NULL AND s.id IS NULL;
SELECT cs.id FROM candidate_sessions cs LEFT JOIN users u ON cs.candidate_user_id = u.id WHERE cs.candidate_user_id IS NOT NULL AND u.id IS NULL;
SELECT eds.id FROM evaluation_day_scores eds LEFT JOIN evaluation_runs er ON eds.run_id = er.id WHERE er.id IS NULL;
SELECT er.id FROM evaluation_runs er LEFT JOIN candidate_sessions cs ON er.candidate_session_id = cs.id WHERE cs.id IS NULL;
SELECT er.id FROM evaluation_runs er LEFT JOIN scenario_versions sv ON er.scenario_version_id = sv.id WHERE sv.id IS NULL;
SELECT fp.id FROM fit_profiles fp LEFT JOIN candidate_sessions cs ON fp.candidate_session_id = cs.id WHERE cs.id IS NULL;
SELECT j.id FROM jobs j LEFT JOIN companies c ON j.company_id = c.id WHERE c.id IS NULL;
SELECT j.id FROM jobs j LEFT JOIN candidate_sessions cs ON j.candidate_session_id = cs.id WHERE j.candidate_session_id IS NOT NULL AND cs.id IS NULL;
SELECT pb.id FROM precommit_bundles pb LEFT JOIN scenario_versions sv ON pb.scenario_version_id = sv.id WHERE sv.id IS NULL;
SELECT ra.id FROM recording_assets ra LEFT JOIN candidate_sessions cs ON ra.candidate_session_id = cs.id WHERE cs.id IS NULL;
SELECT ra.id FROM recording_assets ra LEFT JOIN tasks t ON ra.task_id = t.id WHERE t.id IS NULL;
SELECT sea.id FROM scenario_edit_audit sea LEFT JOIN scenario_versions sv ON sea.scenario_version_id = sv.id WHERE sv.id IS NULL;
SELECT sea.id FROM scenario_edit_audit sea LEFT JOIN users u ON sea.recruiter_id = u.id WHERE u.id IS NULL;
SELECT sv.id FROM scenario_versions sv LEFT JOIN simulations s ON sv.simulation_id = s.id WHERE s.id IS NULL;
SELECT s.id FROM simulations s LEFT JOIN companies c ON s.company_id = c.id WHERE s.company_id IS NOT NULL AND c.id IS NULL;
SELECT s.id FROM simulations s LEFT JOIN users u ON s.created_by = u.id WHERE s.created_by IS NOT NULL AND u.id IS NULL;
SELECT sub.id FROM submissions sub LEFT JOIN candidate_sessions cs ON sub.candidate_session_id = cs.id WHERE sub.candidate_session_id IS NOT NULL AND cs.id IS NULL;
SELECT sub.id FROM submissions sub LEFT JOIN tasks t ON sub.task_id = t.id WHERE sub.task_id IS NOT NULL AND t.id IS NULL;
SELECT td.id FROM task_drafts td LEFT JOIN candidate_sessions cs ON td.candidate_session_id = cs.id WHERE cs.id IS NULL;
SELECT td.id FROM task_drafts td LEFT JOIN tasks t ON td.task_id = t.id WHERE t.id IS NULL;
SELECT td.id FROM task_drafts td LEFT JOIN submissions s ON td.finalized_submission_id = s.id WHERE td.finalized_submission_id IS NOT NULL AND s.id IS NULL;
SELECT t.id FROM tasks t LEFT JOIN simulations s ON t.simulation_id = s.id WHERE t.simulation_id IS NOT NULL AND s.id IS NULL;
SELECT tr.id FROM transcripts tr LEFT JOIN recording_assets ra ON tr.recording_id = ra.id WHERE ra.id IS NULL;
SELECT u.id FROM users u LEFT JOIN companies c ON u.company_id = c.id WHERE u.company_id IS NOT NULL AND c.id IS NULL;
SELECT wg.id FROM workspace_groups wg LEFT JOIN candidate_sessions cs ON wg.candidate_session_id = cs.id WHERE cs.id IS NULL;
SELECT w.id FROM workspaces w LEFT JOIN candidate_sessions cs ON w.candidate_session_id = cs.id WHERE cs.id IS NULL;
SELECT w.id FROM workspaces w LEFT JOIN tasks t ON w.task_id = t.id WHERE t.id IS NULL;

-- Duplicate checks for key unique rules
SELECT email, COUNT(*) FROM users GROUP BY email HAVING COUNT(*) > 1;
SELECT simulation_id, invite_email, COUNT(*) FROM candidate_sessions GROUP BY simulation_id, invite_email HAVING COUNT(*) > 1;
SELECT candidate_session_id, task_id, COUNT(*) FROM submissions GROUP BY candidate_session_id, task_id HAVING COUNT(*) > 1;
SELECT candidate_session_id, task_id, COUNT(*) FROM task_drafts GROUP BY candidate_session_id, task_id HAVING COUNT(*) > 1;
SELECT run_id, day_index, COUNT(*) FROM evaluation_day_scores GROUP BY run_id, day_index HAVING COUNT(*) > 1;
SELECT candidate_session_id, COUNT(*) FROM fit_profiles GROUP BY candidate_session_id HAVING COUNT(*) > 1;
SQL

  cat >"$RUNTIME_SECTION_5_SQL" <<'SQL'
-- Section 5: Enum/status consistency
SELECT DISTINCT status FROM simulations;
SELECT DISTINCT status FROM candidate_sessions;
SELECT DISTINCT status FROM evaluation_runs;
SELECT DISTINCT recommendation FROM evaluation_runs;
SELECT DISTINCT status FROM precommit_bundles;
SELECT DISTINCT status FROM recording_assets;
SELECT DISTINCT status FROM transcripts;
SELECT DISTINCT status FROM jobs;
SELECT DISTINCT role FROM users;
SELECT DISTINCT type FROM tasks;

-- Invalid-domain checks based on current business expectations
SELECT DISTINCT status FROM simulations WHERE status IS NOT NULL AND status NOT IN ('draft','generating','ready_for_review','active_inviting','terminated');
SELECT DISTINCT status FROM evaluation_runs WHERE status IS NOT NULL AND status NOT IN ('pending','running','completed','failed');
SELECT DISTINCT recommendation FROM evaluation_runs WHERE recommendation IS NOT NULL AND recommendation NOT IN ('hire','strong_hire','no_hire','lean_hire');
SELECT DISTINCT status FROM precommit_bundles WHERE status IS NOT NULL AND status NOT IN ('draft','ready','disabled');
SELECT DISTINCT status FROM recording_assets WHERE status IS NOT NULL AND status NOT IN ('uploading','uploaded','processing','ready','failed','deleted','purged');
SELECT DISTINCT status FROM transcripts WHERE status IS NOT NULL AND status NOT IN ('pending','processing','ready','failed');
SELECT DISTINCT role FROM users WHERE role IS NOT NULL AND role NOT IN ('recruiter','candidate','admin');
SELECT DISTINCT type FROM tasks WHERE type IS NOT NULL AND type NOT IN ('design','code','debug','handoff','documentation');
SQL

  cat >"$RUNTIME_SECTION_6_SQL" <<'SQL'
-- Section 6: Temporal integrity
SELECT id FROM jobs WHERE created_at > updated_at;
SELECT id FROM precommit_bundles WHERE created_at > updated_at;
SELECT id FROM evaluation_runs WHERE completed_at IS NOT NULL AND completed_at < started_at;
SELECT id FROM candidate_sessions WHERE started_at IS NOT NULL AND completed_at IS NOT NULL AND completed_at < started_at;
SELECT id FROM candidate_sessions WHERE claimed_at IS NOT NULL AND expires_at IS NOT NULL AND expires_at <= claimed_at;
SELECT id FROM submissions WHERE submitted_at IS NOT NULL AND last_run_at IS NOT NULL AND last_run_at < submitted_at;
SELECT id FROM simulations
WHERE (ready_for_review_at IS NOT NULL AND generating_at IS NOT NULL AND ready_for_review_at < generating_at)
   OR (activated_at IS NOT NULL AND ready_for_review_at IS NOT NULL AND activated_at < ready_for_review_at)
   OR (terminated_at IS NOT NULL AND activated_at IS NOT NULL AND terminated_at < activated_at);
SQL

  cat >"$RUNTIME_SECTION_7_SQL" <<'SQL'
-- Section 7: JSON structure validation
SELECT id FROM simulations WHERE company_context IS NOT NULL AND jsonb_typeof(company_context::jsonb) <> 'object';
SELECT id FROM simulations WHERE ai_eval_enabled_by_day IS NOT NULL AND jsonb_typeof(ai_eval_enabled_by_day::jsonb) <> 'object';
SELECT id FROM simulations WHERE day_window_overrides_json IS NOT NULL AND jsonb_typeof(day_window_overrides_json::jsonb) <> 'object';
SELECT id FROM candidate_sessions WHERE day_windows_json IS NOT NULL AND jsonb_typeof(day_windows_json::jsonb) <> 'array';
SELECT id FROM scenario_versions WHERE task_prompts_json IS NOT NULL AND jsonb_typeof(task_prompts_json::jsonb) NOT IN ('array','object');
SELECT id FROM scenario_versions WHERE rubric_json IS NOT NULL AND jsonb_typeof(rubric_json::jsonb) NOT IN ('array','object');
SELECT id FROM submissions WHERE content_json IS NOT NULL AND jsonb_typeof(content_json::jsonb) <> 'object';
SELECT id FROM task_drafts WHERE content_json IS NOT NULL AND jsonb_typeof(content_json::jsonb) <> 'object';
SELECT id FROM jobs WHERE payload_json IS NOT NULL AND jsonb_typeof(payload_json::jsonb) <> 'object';
SELECT id FROM jobs WHERE result_json IS NOT NULL AND jsonb_typeof(result_json::jsonb) <> 'object';
SELECT id FROM evaluation_runs WHERE raw_report_json IS NOT NULL AND jsonb_typeof(raw_report_json::jsonb) <> 'object';
SELECT id FROM evaluation_runs WHERE metadata_json IS NOT NULL AND jsonb_typeof(metadata_json::jsonb) <> 'object';
SELECT id FROM evaluation_day_scores WHERE rubric_results_json IS NOT NULL AND jsonb_typeof(rubric_results_json::jsonb) <> 'object';
SELECT id FROM evaluation_day_scores WHERE evidence_pointers_json IS NOT NULL AND jsonb_typeof(evidence_pointers_json::jsonb) <> 'array';
SELECT id FROM transcripts WHERE segments_json IS NOT NULL AND jsonb_typeof(segments_json::jsonb) <> 'array';
SELECT id FROM scenario_edit_audit WHERE patch_json IS NOT NULL AND jsonb_typeof(patch_json::jsonb) <> 'object';
SELECT id FROM admin_action_audits WHERE payload_json IS NOT NULL AND jsonb_typeof(payload_json::jsonb) <> 'object';
SQL

  cat >"$RUNTIME_SECTION_8_SQL" <<'SQL'
-- Section 8: Index effectiveness spot checks
EXPLAIN ANALYZE SELECT * FROM users WHERE email = 'qa.recruiter@tenon.test';
EXPLAIN ANALYZE SELECT * FROM candidate_sessions WHERE token = 'qa_db_protocol_token_970001';
EXPLAIN ANALYZE SELECT * FROM tasks WHERE simulation_id = 970001 ORDER BY day_index;
EXPLAIN ANALYZE SELECT * FROM submissions WHERE candidate_session_id = 970001;
EXPLAIN ANALYZE SELECT * FROM task_drafts WHERE candidate_session_id = 970001;
EXPLAIN ANALYZE SELECT * FROM precommit_bundles WHERE scenario_version_id = 970001 AND template_key = 'python-fastapi' AND status = 'ready';
EXPLAIN ANALYZE SELECT * FROM evaluation_runs WHERE candidate_session_id = 970001 ORDER BY started_at DESC;
EXPLAIN ANALYZE SELECT * FROM evaluation_day_scores WHERE run_id = 970001;
EXPLAIN ANALYZE SELECT * FROM recording_assets WHERE candidate_session_id = 970001 AND task_id = 970004 ORDER BY created_at DESC;
EXPLAIN ANALYZE SELECT * FROM transcripts WHERE status = 'ready' ORDER BY created_at DESC;
EXPLAIN ANALYZE SELECT * FROM jobs WHERE company_id = 970001 AND job_type = 'evaluation.fit_profile' AND idempotency_key = 'qa-cs-970001-fit-profile';
EXPLAIN ANALYZE SELECT * FROM jobs WHERE status IN ('queued','running') ORDER BY next_run_at NULLS FIRST, created_at ASC LIMIT 50;
EXPLAIN ANALYZE SELECT * FROM scenario_edit_audit WHERE scenario_version_id = 970001 ORDER BY created_at DESC;
EXPLAIN ANALYZE SELECT * FROM admin_action_audits WHERE action = 'candidate_session_reset' ORDER BY created_at DESC;
SQL

  cat >"$RUNTIME_SECTION_9_SQL" <<'SQL'
-- Section 9: Migration safety
SELECT EXISTS (
  SELECT 1
  FROM information_schema.tables
  WHERE table_schema = 'public' AND table_name = 'alembic_version'
);

SELECT version_num FROM alembic_version;

SELECT COUNT(*) AS public_table_count
FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
SQL

  cat >"$RUNTIME_SECTION_11_SQL" <<'SQL'
-- Section 11: Comprehensive schema coverage audit
DROP TABLE IF EXISTS qa_schema_audit_results;
CREATE TEMP TABLE qa_schema_audit_results (
  category text NOT NULL,
  object_name text NOT NULL,
  check_name text NOT NULL,
  passed boolean NOT NULL,
  details text NOT NULL
);

-- 11.1 NOT NULL constraints: one check per NOT NULL column
DO $$
DECLARE
  rec record;
  v_violations bigint;
BEGIN
  FOR rec IN
    SELECT n.nspname AS schema_name, t.relname AS table_name, a.attname AS column_name
    FROM pg_attribute a
    JOIN pg_class t ON t.oid = a.attrelid
    JOIN pg_namespace n ON n.oid = t.relnamespace
    WHERE n.nspname = 'public'
      AND t.relkind = 'r'
      AND a.attnum > 0
      AND NOT a.attisdropped
      AND a.attnotnull
    ORDER BY n.nspname, t.relname, a.attname
  LOOP
    EXECUTE format('SELECT COUNT(*) FROM %I.%I WHERE %I IS NULL', rec.schema_name, rec.table_name, rec.column_name)
      INTO v_violations;
    INSERT INTO qa_schema_audit_results
    VALUES (
      'constraint_not_null',
      format('%I.%I.%I', rec.schema_name, rec.table_name, rec.column_name),
      'no_null_values',
      v_violations = 0,
      format('null_violations=%s', v_violations)
    );
  END LOOP;
END $$;

-- 11.2 UNIQUE + PRIMARY KEY constraints: one check per constraint
DO $$
DECLARE
  rec record;
  v_violations bigint;
BEGIN
  FOR rec IN
    SELECT
      c.contype,
      n.nspname AS schema_name,
      t.relname AS table_name,
      c.conname AS constraint_name,
      string_agg(format('%I', a.attname), ', ' ORDER BY ord.ordinality) AS cols_expr,
      string_agg(format('%I IS NOT NULL', a.attname), ' AND ' ORDER BY ord.ordinality) AS not_null_expr
    FROM pg_constraint c
    JOIN pg_class t ON t.oid = c.conrelid
    JOIN pg_namespace n ON n.oid = t.relnamespace
    JOIN LATERAL unnest(c.conkey) WITH ORDINALITY AS ord(attnum, ordinality) ON TRUE
    JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ord.attnum
    WHERE n.nspname = 'public'
      AND t.relkind = 'r'
      AND c.contype IN ('p', 'u')
    GROUP BY c.contype, n.nspname, t.relname, c.conname
    ORDER BY n.nspname, t.relname, c.conname
  LOOP
    EXECUTE format(
      'SELECT COUNT(*) FROM (SELECT %s FROM %I.%I WHERE %s GROUP BY %s HAVING COUNT(*) > 1) d',
      rec.cols_expr, rec.schema_name, rec.table_name, rec.not_null_expr, rec.cols_expr
    ) INTO v_violations;

    INSERT INTO qa_schema_audit_results
    VALUES (
      CASE WHEN rec.contype = 'p' THEN 'constraint_primary_key' ELSE 'constraint_unique' END,
      format('%I.%I.%I', rec.schema_name, rec.table_name, rec.constraint_name),
      'duplicate_key_rows',
      v_violations = 0,
      format('duplicate_groups=%s', v_violations)
    );
  END LOOP;
END $$;

-- 11.3 CHECK constraints: one check per constraint
DO $$
DECLARE
  rec record;
  v_violations bigint;
BEGIN
  FOR rec IN
    SELECT
      n.nspname AS schema_name,
      t.relname AS table_name,
      c.conname AS constraint_name,
      pg_get_expr(c.conbin, c.conrelid, true) AS check_expr
    FROM pg_constraint c
    JOIN pg_class t ON t.oid = c.conrelid
    JOIN pg_namespace n ON n.oid = t.relnamespace
    WHERE n.nspname = 'public'
      AND t.relkind = 'r'
      AND c.contype = 'c'
    ORDER BY n.nspname, t.relname, c.conname
  LOOP
    EXECUTE format('SELECT COUNT(*) FROM %I.%I WHERE NOT (%s)', rec.schema_name, rec.table_name, rec.check_expr)
      INTO v_violations;
    INSERT INTO qa_schema_audit_results
    VALUES (
      'constraint_check',
      format('%I.%I.%I', rec.schema_name, rec.table_name, rec.constraint_name),
      'check_expression_holds',
      v_violations = 0,
      format('violating_rows=%s expr=%s', v_violations, rec.check_expr)
    );
  END LOOP;
END $$;

-- 11.4 FOREIGN KEY constraints: one orphan check + action metadata checks per constraint
DO $$
DECLARE
  rec record;
  v_orphans bigint;
  v_delete_action text;
  v_update_action text;
BEGIN
  FOR rec IN
    SELECT
      c.conname AS constraint_name,
      child_ns.nspname AS child_schema,
      child.relname AS child_table,
      parent_ns.nspname AS parent_schema,
      parent.relname AS parent_table,
      c.confdeltype,
      c.confupdtype,
      string_agg(format('c.%I = p.%I', ca.attname, pa.attname), ' AND ' ORDER BY ord_child.ordinality) AS join_expr,
      string_agg(format('c.%I IS NOT NULL', ca.attname), ' AND ' ORDER BY ord_child.ordinality) AS child_not_null_expr,
      min(pa.attname) AS parent_probe_col
    FROM pg_constraint c
    JOIN pg_class child ON child.oid = c.conrelid
    JOIN pg_namespace child_ns ON child_ns.oid = child.relnamespace
    JOIN pg_class parent ON parent.oid = c.confrelid
    JOIN pg_namespace parent_ns ON parent_ns.oid = parent.relnamespace
    JOIN LATERAL unnest(c.conkey) WITH ORDINALITY AS ord_child(attnum, ordinality) ON TRUE
    JOIN LATERAL unnest(c.confkey) WITH ORDINALITY AS ord_parent(attnum, ordinality)
      ON ord_parent.ordinality = ord_child.ordinality
    JOIN pg_attribute ca ON ca.attrelid = child.oid AND ca.attnum = ord_child.attnum
    JOIN pg_attribute pa ON pa.attrelid = parent.oid AND pa.attnum = ord_parent.attnum
    WHERE child_ns.nspname = 'public'
      AND parent_ns.nspname = 'public'
      AND c.contype = 'f'
    GROUP BY
      c.conname, child_ns.nspname, child.relname, parent_ns.nspname, parent.relname,
      c.confdeltype, c.confupdtype
    ORDER BY child_ns.nspname, child.relname, c.conname
  LOOP
    EXECUTE format(
      'SELECT COUNT(*) FROM %I.%I c LEFT JOIN %I.%I p ON %s WHERE %s AND p.%I IS NULL',
      rec.child_schema, rec.child_table, rec.parent_schema, rec.parent_table,
      rec.join_expr, rec.child_not_null_expr, rec.parent_probe_col
    ) INTO v_orphans;

    INSERT INTO qa_schema_audit_results
    VALUES (
      'constraint_fk',
      format('%I.%I.%I', rec.child_schema, rec.child_table, rec.constraint_name),
      'orphan_reference_rows',
      v_orphans = 0,
      format('orphan_rows=%s parent=%I.%I', v_orphans, rec.parent_schema, rec.parent_table)
    );

    v_delete_action := CASE rec.confdeltype
      WHEN 'a' THEN 'NO ACTION'
      WHEN 'r' THEN 'RESTRICT'
      WHEN 'c' THEN 'CASCADE'
      WHEN 'n' THEN 'SET NULL'
      WHEN 'd' THEN 'SET DEFAULT'
      ELSE 'UNKNOWN'
    END;

    v_update_action := CASE rec.confupdtype
      WHEN 'a' THEN 'NO ACTION'
      WHEN 'r' THEN 'RESTRICT'
      WHEN 'c' THEN 'CASCADE'
      WHEN 'n' THEN 'SET NULL'
      WHEN 'd' THEN 'SET DEFAULT'
      ELSE 'UNKNOWN'
    END;

    INSERT INTO qa_schema_audit_results
    VALUES (
      'constraint_fk',
      format('%I.%I.%I', rec.child_schema, rec.child_table, rec.constraint_name),
      'delete_action_defined',
      v_delete_action <> 'UNKNOWN',
      format('on_delete=%s', v_delete_action)
    );

    INSERT INTO qa_schema_audit_results
    VALUES (
      'constraint_fk',
      format('%I.%I.%I', rec.child_schema, rec.child_table, rec.constraint_name),
      'update_action_defined',
      v_update_action <> 'UNKNOWN',
      format('on_update=%s', v_update_action)
    );
  END LOOP;
END $$;

-- 11.5 Triggers
DO $$
DECLARE
  rec record;
  v_count integer := 0;
BEGIN
  FOR rec IN
    SELECT
      n.nspname AS schema_name,
      c.relname AS table_name,
      tg.tgname AS trigger_name,
      tg.tgenabled,
      p.oid IS NOT NULL AS function_exists
    FROM pg_trigger tg
    JOIN pg_class c ON c.oid = tg.tgrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    LEFT JOIN pg_proc p ON p.oid = tg.tgfoid
    WHERE n.nspname = 'public'
      AND NOT tg.tgisinternal
    ORDER BY n.nspname, c.relname, tg.tgname
  LOOP
    v_count := v_count + 1;
    INSERT INTO qa_schema_audit_results
    VALUES (
      'trigger',
      format('%I.%I.%I', rec.schema_name, rec.table_name, rec.trigger_name),
      'enabled_and_function_exists',
      rec.tgenabled <> 'D' AND rec.function_exists,
      format('enabled=%s function_exists=%s', rec.tgenabled, rec.function_exists)
    );
  END LOOP;

  IF v_count = 0 THEN
    INSERT INTO qa_schema_audit_results
    VALUES ('trigger', '(none)', 'user_trigger_inventory', TRUE, 'No user-defined triggers found in public schema');
  END IF;
END $$;

-- 11.6 Functions
DO $$
DECLARE
  rec record;
  v_count integer := 0;
BEGIN
  FOR rec IN
    SELECT
      p.oid,
      n.nspname AS schema_name,
      p.proname AS function_name,
      pg_get_function_identity_arguments(p.oid) AS identity_args
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'public'
    ORDER BY n.nspname, p.proname, pg_get_function_identity_arguments(p.oid)
  LOOP
    v_count := v_count + 1;
    BEGIN
      PERFORM pg_get_functiondef(rec.oid);
      INSERT INTO qa_schema_audit_results
      VALUES (
        'function',
        format('%I.%I(%s)', rec.schema_name, rec.function_name, rec.identity_args),
        'definition_accessible',
        TRUE,
        'definition_loaded'
      );
    EXCEPTION WHEN OTHERS THEN
      INSERT INTO qa_schema_audit_results
      VALUES (
        'function',
        format('%I.%I(%s)', rec.schema_name, rec.function_name, rec.identity_args),
        'definition_accessible',
        FALSE,
        SQLERRM
      );
    END;
  END LOOP;

  IF v_count = 0 THEN
    INSERT INTO qa_schema_audit_results
    VALUES ('function', '(none)', 'function_inventory', TRUE, 'No user-defined functions found in public schema');
  END IF;
END $$;

-- 11.7 Views
DO $$
DECLARE
  rec record;
  v_count integer := 0;
BEGIN
  FOR rec IN
    SELECT table_schema, table_name
    FROM information_schema.views
    WHERE table_schema = 'public'
    ORDER BY table_name
  LOOP
    v_count := v_count + 1;
    BEGIN
      EXECUTE format('SELECT 1 FROM %I.%I LIMIT 0', rec.table_schema, rec.table_name);
      INSERT INTO qa_schema_audit_results
      VALUES (
        'view',
        format('%I.%I', rec.table_schema, rec.table_name),
        'selectable_limit_0',
        TRUE,
        'queryable'
      );
    EXCEPTION WHEN OTHERS THEN
      INSERT INTO qa_schema_audit_results
      VALUES (
        'view',
        format('%I.%I', rec.table_schema, rec.table_name),
        'selectable_limit_0',
        FALSE,
        SQLERRM
      );
    END;
  END LOOP;

  IF v_count = 0 THEN
    INSERT INTO qa_schema_audit_results
    VALUES ('view', '(none)', 'view_inventory', TRUE, 'No views found in public schema');
  END IF;
END $$;

-- 11.8 Permissions
DO $$
DECLARE
  rec record;
  v_has_access boolean;
  v_function_count integer := 0;
BEGIN
  FOR rec IN
    SELECT
      n.nspname AS schema_name,
      c.relname AS object_name,
      c.relkind,
      pg_get_userbyid(c.relowner) AS owner_name
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public'
      AND c.relkind IN ('r', 'p', 'v', 'm', 'S', 'f')
    ORDER BY n.nspname, c.relname
  LOOP
    IF rec.relkind = 'S' THEN
      EXECUTE format(
        'SELECT has_sequence_privilege(current_user, %L, ''USAGE'')',
        format('%I.%I', rec.schema_name, rec.object_name)
      ) INTO v_has_access;
    ELSE
      EXECUTE format(
        'SELECT has_table_privilege(current_user, %L, ''SELECT'')',
        format('%I.%I', rec.schema_name, rec.object_name)
      ) INTO v_has_access;
    END IF;

    INSERT INTO qa_schema_audit_results
    VALUES (
      'permission',
      format('%I.%I', rec.schema_name, rec.object_name),
      'owner_defined',
      rec.owner_name IS NOT NULL,
      format('owner=%s', COALESCE(rec.owner_name, 'NULL'))
    );

    INSERT INTO qa_schema_audit_results
    VALUES (
      'permission',
      format('%I.%I', rec.schema_name, rec.object_name),
      CASE WHEN rec.relkind = 'S' THEN 'current_user_sequence_usage' ELSE 'current_user_select' END,
      COALESCE(v_has_access, FALSE),
      format('has_access=%s relkind=%s', COALESCE(v_has_access, FALSE), rec.relkind)
    );
  END LOOP;

  FOR rec IN
    SELECT
      p.oid,
      n.nspname AS schema_name,
      p.proname AS function_name,
      pg_get_function_identity_arguments(p.oid) AS identity_args
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'public'
    ORDER BY n.nspname, p.proname
  LOOP
    v_function_count := v_function_count + 1;
    INSERT INTO qa_schema_audit_results
    VALUES (
      'permission',
      format('%I.%I(%s)', rec.schema_name, rec.function_name, rec.identity_args),
      'current_user_execute',
      has_function_privilege(current_user, rec.oid, 'EXECUTE'),
      format('has_execute=%s', has_function_privilege(current_user, rec.oid, 'EXECUTE'))
    );
  END LOOP;

  IF v_function_count = 0 THEN
    INSERT INTO qa_schema_audit_results
    VALUES ('permission', '(none)', 'function_execute_privilege_inventory', TRUE, 'No public-schema functions');
  END IF;
END $$;

-- 11.9 Extensions
DO $$
DECLARE
  rec record;
  v_has_plpgsql boolean;
BEGIN
  FOR rec IN
    SELECT extname, extversion FROM pg_extension ORDER BY extname
  LOOP
    INSERT INTO qa_schema_audit_results
    VALUES (
      'extension',
      rec.extname,
      'installed',
      TRUE,
      format('version=%s', rec.extversion)
    );
  END LOOP;

  SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'plpgsql') INTO v_has_plpgsql;
  INSERT INTO qa_schema_audit_results
  VALUES (
    'extension',
    'plpgsql',
    'required_extension_present',
    v_has_plpgsql,
    format('present=%s', v_has_plpgsql)
  );
END $$;

-- 11.10 Sequences
DO $$
DECLARE
  rec record;
  v_last_value bigint;
  v_max_value bigint;
BEGIN
  FOR rec IN
    SELECT
      seq_ns.nspname AS seq_schema,
      seq.relname AS seq_name,
      tbl_ns.nspname AS owner_schema,
      tbl.relname AS owner_table,
      a.attname AS owner_column
    FROM pg_class seq
    JOIN pg_namespace seq_ns ON seq_ns.oid = seq.relnamespace
    LEFT JOIN pg_depend d
      ON d.classid = 'pg_class'::regclass
     AND d.objid = seq.oid
     AND d.deptype = 'a'
    LEFT JOIN pg_class tbl ON tbl.oid = d.refobjid
    LEFT JOIN pg_namespace tbl_ns ON tbl_ns.oid = tbl.relnamespace
    LEFT JOIN pg_attribute a ON a.attrelid = tbl.oid AND a.attnum = d.refobjsubid
    WHERE seq.relkind = 'S'
      AND seq_ns.nspname = 'public'
    ORDER BY seq_ns.nspname, seq.relname
  LOOP
    INSERT INTO qa_schema_audit_results
    VALUES (
      'sequence',
      format('%I.%I', rec.seq_schema, rec.seq_name),
      'owned_by_column',
      rec.owner_table IS NOT NULL AND rec.owner_column IS NOT NULL,
      format('owned_by=%s.%s.%s', COALESCE(rec.owner_schema, 'NULL'), COALESCE(rec.owner_table, 'NULL'), COALESCE(rec.owner_column, 'NULL'))
    );

    IF rec.owner_table IS NOT NULL AND rec.owner_column IS NOT NULL THEN
      EXECUTE format('SELECT last_value FROM %I.%I', rec.seq_schema, rec.seq_name) INTO v_last_value;
      EXECUTE format('SELECT COALESCE(MAX(%I), 0) FROM %I.%I', rec.owner_column, rec.owner_schema, rec.owner_table) INTO v_max_value;

      INSERT INTO qa_schema_audit_results
      VALUES (
        'sequence',
        format('%I.%I', rec.seq_schema, rec.seq_name),
        'last_value_not_behind_owner_column',
        v_last_value >= v_max_value,
        format('last_value=%s owner_max=%s owner=%I.%I.%I', v_last_value, v_max_value, rec.owner_schema, rec.owner_table, rec.owner_column)
      );
    END IF;
  END LOOP;
END $$;

SELECT
  category,
  COUNT(*) AS total_checks,
  COUNT(*) FILTER (WHERE passed) AS passed_checks,
  COUNT(*) FILTER (WHERE NOT passed) AS failed_checks
FROM qa_schema_audit_results
GROUP BY category
ORDER BY category;

SELECT * FROM qa_schema_audit_results WHERE NOT passed ORDER BY category, object_name, check_name;

DO $$
DECLARE
  v_failures integer;
BEGIN
  SELECT COUNT(*) INTO v_failures
  FROM qa_schema_audit_results
  WHERE NOT passed;

  IF v_failures > 0 THEN
    RAISE EXCEPTION 'Comprehensive schema audit failed with % failing checks', v_failures;
  END IF;
END $$;
SQL

  cat >"$RUNTIME_SECTION_10_SQL" <<'SQL'
-- Section 10: Stress and edge cases (runtime-compatible, expected failures allowed)
BEGIN;

-- VARCHAR boundary on users.name VARCHAR(200)
SAVEPOINT sp_len_200_ok;
INSERT INTO users (id, name, email, role, company_id, password_hash, created_at)
VALUES (979001, repeat('a', 200), 'qa.boundary.200@tenon.test', 'recruiter', 970001, NULL, NOW());
-- Expected: success

SAVEPOINT sp_len_201_fail;
INSERT INTO users (id, name, email, role, company_id, password_hash, created_at)
VALUES (979002, repeat('b', 201), 'qa.boundary.201@tenon.test', 'recruiter', 970001, NULL, NOW());
-- Expected: ERROR
ROLLBACK TO SAVEPOINT sp_len_201_fail;

-- Unicode handling
SAVEPOINT sp_unicode;
UPDATE submissions
SET content_text = 'Unicode: 日本語 émojis 🚀💻'
WHERE id = 970001;
SELECT content_text FROM submissions WHERE id = 970001;

-- Empty string vs NULL
SAVEPOINT sp_empty_vs_null;
UPDATE candidate_sessions SET candidate_email = '' WHERE id = 970001;
SELECT id, candidate_email, candidate_email IS NULL AS is_null_after_empty FROM candidate_sessions WHERE id = 970001;
UPDATE candidate_sessions SET candidate_email = NULL WHERE id = 970001;
SELECT id, candidate_email, candidate_email IS NULL AS is_null_after_null FROM candidate_sessions WHERE id = 970001;

-- Large JSON payload
SAVEPOINT sp_large_json;
INSERT INTO jobs (
  id, job_type, status, attempt, max_attempts, idempotency_key, payload_json, result_json, last_error,
  created_at, updated_at, next_run_at, locked_at, locked_by, correlation_id, company_id, candidate_session_id
)
VALUES (
  '97900300-0000-0000-0000-000000000001', 'qa.large_json', 'queued', 0, 5, 'qa-large-json-979001',
  json_build_object('blob', repeat('x', 50000)), NULL, NULL, NOW(), NOW(), NOW(), NULL, NULL, 'qa-large-json', 970001, 970001
);

ROLLBACK;
SQL

  cat >"$RUNTIME_SEED_SQL" <<'SQL'
-- Runtime-compatible deterministic QA seed for current local tenon schema
BEGIN;
SET TIME ZONE 'UTC';

INSERT INTO companies (id, name, created_at)
VALUES
  (970001, 'qa_db_protocol_company', NOW()),
  (970004, 'qa_db_protocol_company_2', NOW());

INSERT INTO items (id, name, description, created_at)
VALUES
  (970001, 'qa_item_primary', 'seed item for full coverage', NOW()),
  (970002, 'qa_item_secondary', 'seed item for full coverage duplicate tests', NOW());

INSERT INTO users (id, name, email, role, company_id, password_hash, created_at)
VALUES
  (970001, 'QA Recruiter', 'qa.recruiter@tenon.test', 'recruiter', 970001, NULL, NOW()),
  (970002, 'QA Candidate', 'qa.candidate@tenon.test', 'candidate', NULL, NULL, NOW()),
  (970003, 'QA Admin', 'qa.admin@tenon.test', 'admin', 970001, NULL, NOW());

INSERT INTO simulations (
  id, company_id, title, role, tech_stack, seniority, scenario_template,
  created_by, status, created_at, focus, template_key, generating_at,
  ready_for_review_at, activated_at, terminated_at, company_context,
  ai_notice_version, ai_notice_text, ai_eval_enabled_by_day, terminated_reason,
  terminated_by_recruiter_id, day_window_start_local, day_window_end_local,
  day_window_overrides_enabled, day_window_overrides_json
)
VALUES (
  970001, 970001, 'QA Protocol Backend Simulation', 'Backend Engineer', 'Python,FastAPI,PostgreSQL',
  'senior', 'default-5day-node-postgres', 970001, 'active_inviting', NOW() - INTERVAL '7 days',
  'Protocol coverage run', 'python-fastapi', NOW() - INTERVAL '7 days', NOW() - INTERVAL '6 days',
  NOW() - INTERVAL '5 days', NULL, '{"domain":"hiring-tech"}'::json, 'v1',
  'AI is used to generate and evaluate this simulation.',
  '{"1":true,"2":true,"3":true,"4":true,"5":true}'::json,
  'qa_fk_cascade_sample', 970001, '09:00:00', '17:00:00', FALSE, NULL
);

INSERT INTO scenario_versions (
  id, simulation_id, version_index, status, storyline_md, task_prompts_json, rubric_json,
  focus_notes, template_key, tech_stack, seniority, model_name, model_version,
  prompt_version, rubric_version, locked_at, created_at
)
VALUES
  (
    970001, 970001, 1, 'locked', '# Scenario v1', '[{"day":1,"prompt":"Design API contract"}]'::json, '{"communication":20}'::json,
    'Initial approved version', 'python-fastapi', 'Python,FastAPI,PostgreSQL', 'senior',
    'gpt-5.4', '2026-03-18', 'sim-v3', 'rubric-v2', NOW() - INTERVAL '6 days', NOW() - INTERVAL '7 days'
  ),
  (
    970002, 970001, 2, 'ready', '# Scenario v2', '[{"day":2,"prompt":"Implement endpoint"}]'::json, '{"implementation":30}'::json,
    'Secondary version for unique/cascade tests', 'python-fastapi', 'Python,FastAPI,PostgreSQL', 'senior',
    'gpt-5.4', '2026-03-18', 'sim-v3', 'rubric-v2', NOW() - INTERVAL '5 days', NOW() - INTERVAL '6 days'
  );

UPDATE simulations
SET active_scenario_version_id = 970001,
    pending_scenario_version_id = 970002
WHERE id = 970001;

INSERT INTO tasks (id, simulation_id, day_index, type, title, description, starter_code_path, test_file_path, max_score, template_repo)
VALUES
  (970001, 970001, 1, 'design', 'Design', 'Design task', NULL, NULL, 20, 'tenon-hire-dev/tenon-template-python-fastapi'),
  (970002, 970001, 2, 'code', 'Implement', 'Coding task', 'app/main.py', 'tests/test_main.py', 20, 'tenon-hire-dev/tenon-template-python-fastapi'),
  (970003, 970001, 3, 'debug', 'Debug', 'Debug task', 'app/service.py', 'tests/test_service.py', 20, 'tenon-hire-dev/tenon-template-python-fastapi'),
  (970004, 970001, 4, 'handoff', 'Demo', 'Handoff task', NULL, NULL, 20, 'tenon-hire-dev/tenon-template-python-fastapi'),
  (970005, 970001, 5, 'documentation', 'Essay', 'Reflection task', NULL, NULL, 20, 'tenon-hire-dev/tenon-template-python-fastapi');

INSERT INTO candidate_sessions (
  id, simulation_id, candidate_user_id, invite_email, token, status, started_at, completed_at,
  candidate_name, expires_at, candidate_email, candidate_auth0_sub, claimed_at, invite_email_status,
  invite_email_error, invite_email_last_attempt_at, invite_email_sent_at, candidate_auth0_email,
  scheduled_start_at, candidate_timezone, schedule_locked_at, invite_email_verified_at, day_windows_json, github_username,
  scenario_version_id
)
VALUES
  (
    970001, 970001, 970002, 'qa.candidate@tenon.test', 'qa_db_protocol_token_970001', 'completed',
    NOW() - INTERVAL '5 days', NOW() - INTERVAL '1 day', 'QA Candidate', NOW() + INTERVAL '7 days',
    'qa.candidate@tenon.test', 'auth0|qa-candidate', NOW() - INTERVAL '5 days', 'sent',
    NULL, NOW() - INTERVAL '6 days', NOW() - INTERVAL '6 days', 'qa.candidate@tenon.test',
    NOW() - INTERVAL '5 days', 'America/New_York', NOW() - INTERVAL '5 days', NOW() - INTERVAL '5 days',
    '[{"dayIndex":1,"windowStartAt":"2026-03-10T14:00:00Z","windowEndAt":"2026-03-10T22:00:00Z"}]'::json, 'qa-candidate-gh',
    970001
  ),
  (
    970002, 970001, 970002, 'qa.candidate.2@tenon.test', 'qa_db_protocol_token_970002', 'active',
    NOW() - INTERVAL '4 days', NULL, 'QA Candidate 2', NOW() + INTERVAL '7 days',
    'qa.candidate.2@tenon.test', 'auth0|qa-candidate-2', NOW() - INTERVAL '4 days', 'sent',
    NULL, NOW() - INTERVAL '5 days', NOW() - INTERVAL '5 days', 'qa.candidate.2@tenon.test',
    NOW() - INTERVAL '4 days', 'America/New_York', NOW() - INTERVAL '4 days', NOW() - INTERVAL '4 days',
    '[{"dayIndex":1,"windowStartAt":"2026-03-11T14:00:00Z","windowEndAt":"2026-03-11T22:00:00Z"}]'::json, 'qa-candidate-gh-2',
    970002
  );

INSERT INTO candidate_day_audits (id, candidate_session_id, day_index, cutoff_at, cutoff_commit_sha, eval_basis_ref, created_at)
VALUES
  (970001, 970001, 2, NOW() - INTERVAL '3 days', 'qa_cutoff_sha_d2', 'refs/heads/day2', NOW() - INTERVAL '3 days'),
  (970002, 970001, 3, NOW() - INTERVAL '2 days', 'qa_cutoff_sha_d3', 'refs/heads/day3', NOW() - INTERVAL '2 days');

INSERT INTO workspace_groups (
  id, candidate_session_id, workspace_key, template_repo_full_name, repo_full_name, default_branch, base_template_sha, created_at
)
VALUES
  (
    '97000100-0000-0000-0000-000000000001', 970001, 'qa-shared-workspace',
    'tenon-hire-dev/tenon-template-python-fastapi', 'tenon-qa/qa-sim-970001', 'main', 'base_sha_970001', NOW() - INTERVAL '5 days'
  ),
  (
    '97000100-0000-0000-0000-000000000002', 970001, 'qa-shared-workspace-2',
    'tenon-hire-dev/tenon-template-python-fastapi', 'tenon-qa/qa-sim-970001', 'main', 'base_sha_970001', NOW() - INTERVAL '5 days'
  );

INSERT INTO workspaces (
  id, candidate_session_id, task_id, template_repo_full_name, repo_full_name, repo_id, default_branch, created_at,
  latest_commit_sha, last_workflow_run_id, last_workflow_conclusion, last_test_summary_json, base_template_sha,
  codespace_name, codespace_url, codespace_state, workspace_group_id
)
VALUES
  (
    '97000200-0000-0000-0000-000000000001', 970001, 970002,
    'tenon-hire-dev/tenon-template-python-fastapi', 'tenon-qa/qa-sim-970001-task-970002',
    123456789, 'main', NOW() - INTERVAL '5 days', 'latest_commit_sha_970001', 'workflow_run_970001',
    'success', '{"testsPassed":12,"testsFailed":0}', 'base_sha_970001',
    'qa-codespace-970001', 'https://github.com/codespaces/qa-codespace-970001', 'available',
    '97000100-0000-0000-0000-000000000001'
  ),
  (
    '97000200-0000-0000-0000-000000000002', 970001, 970003,
    'tenon-hire-dev/tenon-template-python-fastapi', 'tenon-qa/qa-sim-970001-task-970003',
    123456790, 'main', NOW() - INTERVAL '4 days', 'latest_commit_sha_970002', 'workflow_run_970002',
    'success', '{"testsPassed":11,"testsFailed":1}', 'base_sha_970001',
    'qa-codespace-970002', 'https://github.com/codespaces/qa-codespace-970002', 'available',
    '97000100-0000-0000-0000-000000000002'
  );

INSERT INTO precommit_bundles (
  id, scenario_version_id, template_key, status, patch_text, storage_ref, content_sha256, base_template_sha, applied_commit_sha, created_at, updated_at
)
VALUES
  (
    970001, 970001, 'python-fastapi', 'ready', 'diff --git a/a b/a', NULL, repeat('a', 64), 'base_sha_970001', 'applied_sha_970001',
    NOW() - INTERVAL '6 days', NOW() - INTERVAL '5 days'
  ),
  (
    970002, 970001, 'node-express-ts', 'ready', 'diff --git a/b b/b', NULL, repeat('b', 64), 'base_sha_970001', 'applied_sha_970002',
    NOW() - INTERVAL '6 days', NOW() - INTERVAL '5 days'
  );

INSERT INTO recording_assets (
  id, candidate_session_id, task_id, storage_key, content_type, bytes, status, created_at
)
VALUES
  (970001, 970001, 970004, 'qa/recordings/970001.mp4', 'video/mp4', 1048576, 'ready', NOW() - INTERVAL '2 days'),
  (970002, 970001, 970005, 'qa/recordings/970002.mp4', 'video/mp4', 1048577, 'uploaded', NOW() - INTERVAL '2 days');

INSERT INTO transcripts (
  id, recording_id, text, segments_json, model_name, last_error, status, created_at
)
VALUES
  (970001, 970001, 'Candidate demo transcript', '[{"start":0,"end":1,"text":"hello"}]'::json, 'whisper-1', NULL, 'ready', NOW() - INTERVAL '2 days'),
  (970002, 970002, 'Candidate demo transcript 2', '[{"start":0,"end":1,"text":"hello again"}]'::json, 'whisper-1', NULL, 'processing', NOW() - INTERVAL '2 days');

INSERT INTO submissions (
  id, candidate_session_id, task_id, submitted_at, content_text, code_repo_path, tests_passed, tests_failed, test_output, last_run_at, commit_sha, workflow_run_id, diff_summary_json, content_json, recording_id
)
VALUES
  (970001, 970001, 970001, NOW() - INTERVAL '5 days', 'Day1 submission', NULL, NULL, NULL, NULL, NOW() - INTERVAL '5 days', NULL, NULL, NULL, '{"day":1}'::json, NULL),
  (970002, 970001, 970002, NOW() - INTERVAL '4 days', 'Day2 submission', 'repo/path', 12, 0, 'ok', NOW() - INTERVAL '4 days', 'sha2', 'wf2', '{"files":3}', '{"day":2}'::json, NULL),
  (970003, 970001, 970003, NOW() - INTERVAL '3 days', 'Day3 submission', 'repo/path', 10, 1, 'minor fail', NOW() - INTERVAL '3 days', 'sha3', 'wf3', '{"files":5}', '{"day":3}'::json, NULL),
  (970004, 970001, 970004, NOW() - INTERVAL '2 days', 'Day4 submission', NULL, NULL, NULL, NULL, NOW() - INTERVAL '2 days', NULL, NULL, NULL, '{"day":4}'::json, 970001),
  (970005, 970001, 970005, NOW() - INTERVAL '1 day', 'Day5 submission', NULL, NULL, NULL, NULL, NOW() - INTERVAL '1 day', NULL, NULL, NULL, '{"day":5}'::json, 970002);

INSERT INTO task_drafts (
  id, candidate_session_id, task_id, content_text, content_json, updated_at, finalized_at, finalized_submission_id
)
VALUES
  (970001, 970001, 970002, 'Draft day2', '{"draft":true}'::json, NOW() - INTERVAL '4 days', NOW() - INTERVAL '4 days', 970002),
  (970002, 970001, 970003, 'Draft day3', '{"draft":true}'::json, NOW() - INTERVAL '3 days', NOW() - INTERVAL '3 days', 970003);

INSERT INTO jobs (
  id, job_type, status, attempt, max_attempts, idempotency_key, payload_json, result_json, last_error,
  created_at, updated_at, next_run_at, locked_at, locked_by, correlation_id, company_id, candidate_session_id
)
VALUES
  (
    '97000300-0000-0000-0000-000000000001', 'scenario.generate', 'succeeded', 1, 5, 'qa-sim-970001-scenario-generate',
    '{"simulationId":970001}'::json, '{"ok":true}'::json, NULL, NOW() - INTERVAL '7 days', NOW() - INTERVAL '6 days',
    NOW() - INTERVAL '6 days', NULL, NULL, 'qa-corr-970001', 970001, 970001
  ),
  (
    '97000300-0000-0000-0000-000000000002', 'evaluation.fit_profile', 'succeeded', 1, 5, 'qa-cs-970001-fit-profile',
    '{"candidateSessionId":970001}'::json, '{"ok":true}'::json, NULL, NOW() - INTERVAL '1 day', NOW() - INTERVAL '15 hours',
    NOW() - INTERVAL '15 hours', NULL, NULL, 'qa-corr-970002', 970001, 970001
  );

INSERT INTO evaluation_runs (
  id, candidate_session_id, scenario_version_id, status, started_at, completed_at, model_name, model_version,
  prompt_version, rubric_version, job_id, basis_fingerprint, overall_fit_score, recommendation, confidence,
  generated_at, raw_report_json, error_code, metadata_json, day2_checkpoint_sha, day3_final_sha, cutoff_commit_sha, transcript_reference
)
VALUES (
  970001, 970001, 970001, 'completed', NOW() - INTERVAL '16 hours', NOW() - INTERVAL '15 hours',
  'gpt-5.4', '2026-03-18', 'eval-v2', 'rubric-v2', '97000300-0000-0000-0000-000000000002', 'basis_fp_970001',
  87.5, 'strong_hire', 0.91, NOW() - INTERVAL '15 hours',
  '{"summary":"Strong implementation and communication"}'::json, NULL,
  '{"jobId":"97000300-0000-0000-0000-000000000002","source":"qa_seed"}'::json,
  'checkpoint_sha_d2', 'final_sha_d3', 'cutoff_sha_d3', 'transcript:970001'
);

INSERT INTO evaluation_day_scores (
  id, run_id, day_index, score, rubric_results_json, evidence_pointers_json, created_at
)
VALUES
  (970011, 970001, 1, 82.0, '{"communication":4,"clarity":4}'::json, '[{"type":"submission","id":970001}]'::json, NOW() - INTERVAL '15 hours'),
  (970012, 970001, 2, 88.0, '{"implementation":4.5,"tests":4.5}'::json, '[{"type":"submission","id":970002}]'::json, NOW() - INTERVAL '15 hours'),
  (970013, 970001, 3, 90.0, '{"debugging":4.5,"rootCause":4.5}'::json, '[{"type":"submission","id":970003}]'::json, NOW() - INTERVAL '15 hours'),
  (970014, 970001, 4, 86.0, '{"demo":4.3,"communication":4.3}'::json, '[{"type":"submission","id":970004}]'::json, NOW() - INTERVAL '15 hours'),
  (970015, 970001, 5, 91.0, '{"reflection":4.6,"judgment":4.5}'::json, '[{"type":"submission","id":970005}]'::json, NOW() - INTERVAL '15 hours');

INSERT INTO fit_profiles (id, candidate_session_id, generated_at)
VALUES (970001, 970001, NOW() - INTERVAL '14 hours');

INSERT INTO scenario_edit_audit (
  id, scenario_version_id, recruiter_id, patch_json, created_at
)
VALUES (
  970001, 970001, 970001, '{"field":"focus_notes","old":"Initial","new":"Edited"}'::json, NOW() - INTERVAL '5 days'
);

INSERT INTO admin_action_audits (
  id, actor_type, actor_id, action, target_type, target_id, payload_json, created_at
)
VALUES (
  'adm_000000000000000000000000000000000001', 'admin', '970003', 'candidate_session_reset',
  'candidate_session', '970001', '{"reason":"qa_seed_reset","dryRun":false}'::json, NOW() - INTERVAL '13 hours'
);

COMMIT;
SQL

  cat >"$RUNTIME_CLEANUP_SQL" <<'SQL'
-- Runtime-compatible cleanup for deterministic QA seed
BEGIN;

DELETE FROM admin_action_audits
WHERE id = 'adm_000000000000000000000000000000000001';

DELETE FROM scenario_edit_audit
WHERE id = 970001 OR scenario_version_id = 970001;

DELETE FROM evaluation_day_scores
WHERE run_id = 970001 OR id BETWEEN 970011 AND 970015;

DELETE FROM evaluation_runs
WHERE id = 970001
   OR job_id IN (
        '97000300-0000-0000-0000-000000000001',
        '97000300-0000-0000-0000-000000000002'
     );

DELETE FROM fit_profiles
WHERE id = 970001 OR candidate_session_id = 970001;

DELETE FROM jobs
WHERE id IN (
  '97000300-0000-0000-0000-000000000001',
  '97000300-0000-0000-0000-000000000002'
)
   OR idempotency_key IN ('qa-sim-970001-scenario-generate', 'qa-cs-970001-fit-profile');

DELETE FROM task_drafts
WHERE id = 970001 OR candidate_session_id = 970001;

DELETE FROM transcripts
WHERE id IN (970001, 970002) OR recording_id IN (970001, 970002);

DELETE FROM submissions
WHERE id BETWEEN 970001 AND 970005 OR candidate_session_id = 970001;

DELETE FROM recording_assets
WHERE id IN (970001, 970002) OR candidate_session_id = 970001;

DELETE FROM workspaces
WHERE id = '97000200-0000-0000-0000-000000000001' OR candidate_session_id = 970001;

DELETE FROM workspace_groups
WHERE id = '97000100-0000-0000-0000-000000000001' OR candidate_session_id = 970001;

DELETE FROM precommit_bundles
WHERE id = 970001 OR scenario_version_id = 970001;

DELETE FROM candidate_day_audits
WHERE id IN (970001, 970002) OR candidate_session_id = 970001;

DELETE FROM candidate_sessions
WHERE id IN (970001, 970002)
   OR token IN ('qa_db_protocol_token_970001', 'qa_db_protocol_token_970002');

DELETE FROM tasks
WHERE id BETWEEN 970001 AND 970005 OR simulation_id = 970001;

UPDATE simulations
SET active_scenario_version_id = NULL,
    pending_scenario_version_id = NULL
WHERE id = 970001 OR title = 'QA Protocol Backend Simulation';

DELETE FROM scenario_versions
WHERE id = 970001 OR simulation_id = 970001;

DELETE FROM simulations
WHERE id = 970001 OR title = 'QA Protocol Backend Simulation';

DELETE FROM users
WHERE id IN (970001, 970002, 970003)
   OR email IN ('qa.recruiter@tenon.test', 'qa.candidate@tenon.test', 'qa.admin@tenon.test');

DELETE FROM items
WHERE id IN (970001, 970002)
   OR name IN ('qa_item_primary', 'qa_item_secondary');

DELETE FROM companies
WHERE id IN (970001, 970004)
   OR name IN ('qa_db_protocol_company', 'qa_db_protocol_company_2');

COMMIT;
SQL
}

headr "Pre-flight"

require_cmd psql
require_cmd python3
require_cmd poetry

if [[ ! -f "$ENV_FILE" ]]; then
  fail "Missing env file: $ENV_FILE"
  exit 1
fi

rm -rf "$RESULTS_DIR"
mkdir -p "$RESULTS_DIR" "$ARTIFACTS_DIR" "$RESULTS_LOGS_DIR" "$RESULTS_SQL_DIR"
ok "Results directory: $RESULTS_DIR"
ok "Artifacts directory: $ARTIFACTS_DIR"

set -a
# shellcheck source=/dev/null
source "$ENV_FILE"
set +a

DB_URL="${TENON_DATABASE_URL_SYNC:-${TENON_DATABASE_URL:-}}"
if [[ -z "$DB_URL" ]]; then
  fail "TENON_DATABASE_URL_SYNC or TENON_DATABASE_URL is not set in $ENV_FILE"
  exit 1
fi
DB_URL="${DB_URL/postgresql+asyncpg:/postgresql:}"

if [[ $ALLOW_NONLOCAL -ne 1 ]]; then
  python3 - "$DB_URL" <<'PY'
import sys
from urllib.parse import urlparse

url = sys.argv[1]
parsed = urlparse(url)
host = (parsed.hostname or "").lower()
db_name = parsed.path.lstrip("/")

if host not in {"localhost", "127.0.0.1"} or db_name != "tenon":
    print(
        f"Refusing to run: expected local DB localhost/127.0.0.1 and database 'tenon', got host='{host}' db='{db_name}'.",
        file=sys.stderr,
    )
    sys.exit(1)
PY
fi

info "Database URL: $DB_URL"
init_summary_files

headr "Database Connectivity"
run_cmd_step "00_connection_check" \
  psql "$DB_URL" -v ON_ERROR_STOP=1 -c "SELECT current_database(), current_user, now();"
ok "Database connection verified"

if [[ $SKIP_MIGRATIONS -ne 1 ]]; then
  headr "Applying Migrations"
  run_cmd_step "00_migrations" \
    bash -lc "cd \"$BACKEND_ROOT\" && poetry run alembic upgrade head && poetry run alembic current"
  ok "Migrations applied"
else
  warn "Skipping migrations (--skip-migrations)"
  append_summary_row "00_migrations" "positive" "SKIPPED" "0" "0" "0" "-"
fi

write_runtime_sql_artifacts
headr "Pre-run Deterministic Cleanup"
run_sql_file "00a_precleanup" "$RUNTIME_CLEANUP_SQL" 1

headr "Running Read-only Sections"
run_sql_file "01_section_1_schema_verification" "$RUNTIME_SECTION_1_SQL" 1
run_sql_file "02_section_4_referential_integrity" "$RUNTIME_SECTION_4_SQL" 1
run_sql_file "03_section_5_enum_status" "$RUNTIME_SECTION_5_SQL" 1
run_sql_file "04_section_6_temporal" "$RUNTIME_SECTION_6_SQL" 1
run_sql_file "05_section_7_json_validation" "$RUNTIME_SECTION_7_SQL" 1
run_sql_file "06_section_8_index_effectiveness" "$RUNTIME_SECTION_8_SQL" 1
run_sql_file "07_section_9_migration_safety" "$RUNTIME_SECTION_9_SQL" 1
run_sql_file "07b_section_11_full_schema_coverage" "$RUNTIME_SECTION_11_SQL" 1

headr "Loading Deterministic QA Seed Data"
run_sql_file "08_seed" "$RUNTIME_SEED_SQL" 1

headr "Running Write Sections"
run_sql_file "09_section_2_constraint_enforcement" "$RUNTIME_SECTION_2_SQL" 1
run_sql_file "10_section_3_lifecycle" "$RUNTIME_SECTION_3_SQL" 1
run_sql_file "11_section_10_stress_edge" "$RUNTIME_SECTION_10_SQL" 0 "${NEGATIVE_EXPECTED_ERRORS["11_section_10_stress_edge"]}"

if [[ $SKIP_CLEANUP -ne 1 ]]; then
  headr "Cleanup"
  run_sql_file "12_cleanup" "$RUNTIME_CLEANUP_SQL" 1
else
  warn "Skipping cleanup (--skip-cleanup)"
  append_summary_row "12_cleanup" "positive" "SKIPPED" "0" "0" "0" "-"
fi

headr "Done"
finalize_summary
ok "Database QA pass completed."
ok "Final Result: $OVERALL_STATUS"
info "Artifacts are in: $ARTIFACTS_DIR"
info "Report: $REPORT_MD"
info "Negative-check report: $NEGATIVE_CHECKS_MD"
