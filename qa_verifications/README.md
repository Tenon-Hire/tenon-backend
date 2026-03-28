# QA Verifications

This directory contains QA runner scripts plus latest report snapshots.

## Runners

- API endpoints QA: `./qa_verifications/API-Endpoints-QA/run_api_qa.sh`
- Database protocol QA: `./qa_verifications/Database-Protocol-QA/run_db_protocol_qa.sh`
- Service logic QA: `./qa_verifications/Service-Logic-QA/run-service-logic-qa.sh`

Each runner overwrites its `*_qa_latest/` directory on every run.

## Latest Directory Contract

Each `*_qa_latest/` directory contains:

- exactly one primary markdown report (`*_qa_report.md`)
- optional `artifacts/` directory with logs/JSON/HTML outputs

`artifacts/` is runtime-generated and may be excluded from source control. For that reason, report files should reference artifact paths as plain code paths (not required markdown links).

## Generated Artifact References

Canonical docs now also generate supporting artifacts under `code-quality/documentation/latest/artifacts/`:

- `openapi_snapshot.json`
- `api_endpoint_matrix.md`
- `api_endpoint_matrix.json`
- `docs_inventory.md`
- `env_inventory.md`
- `docstring_audit.json`

QA reports can refer to these generated files when documenting cross-checks, but should not assume they are committed unless regenerated in the current branch.
