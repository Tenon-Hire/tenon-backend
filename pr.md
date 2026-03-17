## 1. Title
Issue #222: Recruiter Candidate Comparison API (table-ready simulation candidate summary rows)

## 2. TL;DR
Adds recruiter endpoint `GET /api/simulations/{simulation_id}/candidates/compare` that returns table-ready candidate summary rows for a simulation (status, fit-profile status, score/recommendation, day completion, display names) without fetching full fit-profile reports per candidate.

## 3. Problem / Why
- Recruiter compare table needed compact backend summaries per candidate session.
- Fetching full fit-profile payloads per candidate is inefficient for compare-table rendering.
- Endpoint had to be stable, tenant-safe, and owner-scoped.

## 4. What changed
- Added endpoint: `GET /api/simulations/{simulation_id}/candidates/compare`.
- Added compare-summary service/query logic in [`app/services/simulations/candidates_compare.py`](/Users/robelmelaku/Desktop/tenon-backend-wip/app/services/simulations/candidates_compare.py).
- Added response schema/DTO in [`app/schemas/simulations_compare.py`](/Users/robelmelaku/Desktop/tenon-backend-wip/app/schemas/simulations_compare.py).
- Added router logging (`simulationId`, `recruiterId`, `rowCount`, `latencyMs`) in [`app/api/routers/simulations_routes/candidates_compare.py`](/Users/robelmelaku/Desktop/tenon-backend-wip/app/api/routers/simulations_routes/candidates_compare.py).
- Added tests covering schema/scoping/derivation/ordering/timestamps:
  - [`tests/integration/api/test_simulations_candidates_compare_api.py`](/Users/robelmelaku/Desktop/tenon-backend-wip/tests/integration/api/test_simulations_candidates_compare_api.py)
  - [`tests/unit/test_simulations_candidates_compare_service.py`](/Users/robelmelaku/Desktop/tenon-backend-wip/tests/unit/test_simulations_candidates_compare_service.py)
  - [`tests/unit/test_recruiter_simulations_router.py`](/Users/robelmelaku/Desktop/tenon-backend-wip/tests/unit/test_recruiter_simulations_router.py)
- Added manual QA evidence bundle under `.qa/issue222/manual_qa_20260316_213251/`.

## 5. API contract
`GET /api/simulations/{simulation_id}/candidates/compare`

Response:
- `simulationId`
- `candidates[]`

Per candidate:
- `candidateSessionId`
- `candidateName`
- `candidateDisplayName`
- `status`
- `fitProfileStatus`
- `overallFitScore`
- `recommendation`
- `dayCompletion`
- `updatedAt`

Contract notes:
- `overallFitScore` and `recommendation` are nullable.
- `candidateName` and `candidateDisplayName` are non-null due to deterministic anonymized fallback when no usable real name exists.

## 6. Auth / scoping behavior
- Recruiter-only endpoint (`ensure_recruiter`).
- Owner-only + company-scoped simulation access enforcement.
- `404` for unknown simulation.
- `403` for forbidden access to an existing simulation.

## 7. Status + field derivation
`fitProfileStatus` derivation:
- `ready` when a ready fit/evaluation output exists (latest successful evaluation run or fit-profile generated timestamp).
- `generating` when latest run is `pending`/`running` or an active evaluation job is queued/running.
- `failed` when latest run is `failed` and no ready output exists.
- `none` otherwise.

Candidate `status` derivation:
- `evaluated` when `fitProfileStatus == "ready"`.
- `completed` when all day flags are complete, or candidate session completion indicators exist.
- `in_progress` when partial day progress/session progress indicators exist.
- `scheduled` otherwise.

`updatedAt` precedence:
1. fit/eval timestamps
2. candidate-session activity timestamps
3. candidate-session created timestamp
4. defensive UTC-now fallback only if no candidate-row timestamps exist

## 8. Ordering / rendering contract
- Rows are ordered by `CandidateSession.id ASC`.
- Trimmed real candidate name is preferred when present.
- Deterministic anonymized fallback labels are used when no usable name exists (`Candidate A`, `Candidate B`, ...).
- `candidateDisplayName` is the preferred UI field and currently mirrors `candidateName`.

## 9. Performance notes
- Compare endpoint uses a fixed small number of queries in the implemented path (access check, candidate summary, day-completion aggregate).
- No N+1 per candidate in the implemented code path.
- Reads summary/status fields only; no full fit-profile report blob loading.

## 10. Testing / validation
Commands run and passed for implementation validation:

```bash
poetry run ruff check app tests
poetry run ruff format --check app tests
poetry run pytest
./precommit.sh
```

- Full repository suite passed.
- Coverage reached `99.02%` (`coverage.xml` line-rate `0.9902`).
- Precommit checks passed.

## 11. Manual QA verification
Manual runtime QA verdict: `PASS`.

Environment:
- Dedicated Postgres QA database: `tenon_issue222_qa_20260316_213251`.
- Migrations run with: `poetry run alembic upgrade head`.
- Local backend server started with: `poetry run uvicorn app.api.main:app --host 127.0.0.1 --port 8007`.
- Real HTTP requests executed via `curl`.
- DB verification executed via `psql`.

Evidence bundle path:
- `.qa/issue222/manual_qa_20260316_213251/`

Key evidence files:
- `README.md`
- `verdict.json`
- `responses/`
- `sql/`
- `server.log`
- `commands.txt`
- `commands_runtime_trace.txt`

Scenarios passed:
1. empty simulation -> `200`, `candidates: []`
2. authorized owner compare -> `200`
3. wrong company recruiter -> `403`
4. same-company non-owner recruiter -> `403`
5. unknown simulation -> `404`
6. `updatedAt` precedence -> PASS
7. `dayCompletion` correctness -> PASS

Findings verified in manual QA:
- Response schema keys were stable.
- Ordering was deterministic by `candidateSessionId ASC`.
- Real-name trimming worked (`"   Ada Lovelace   " -> "Ada Lovelace"`).
- Anonymized fallback worked (`Candidate A`, etc.).
- Evaluated candidate returned `overallFitScore=0.84` and `recommendation="hire"`.
- Unevaluated candidates returned null fit fields.
- Cross-simulation leakage check passed.
- `updatedAt` matched candidate/eval timestamps, not simulation-level timestamps.
- `dayCompletion` matched DB task/submission state.

## 12. Risks / assumptions
- `candidateName` and `candidateDisplayName` currently resolve to the same display value for compatibility.
- `updatedAt` uses UTC-now only as a defensive last-resort fallback when no candidate-row timestamps exist.
- `recommendation` is returned only when it matches allowed evaluator recommendation values.
- Direct per-request SQL-count instrumentation was limited because `pg_stat_statements` was not fully usable in the local Postgres setup; N+1 risk was instead checked by fixed-query code-path review plus runtime endpoint behavior.

## 13. Rollout / demo notes
- Invite candidates under one simulation.
- Generate fit profiles / evaluation runs.
- Call compare endpoint.
- Render returned rows directly in compare table without per-candidate fit-profile fetches.

## 14. Ready for PR raise
- Implementation complete.
- Automated validation green.
- Manual QA green.
- Ready for PR raise.
