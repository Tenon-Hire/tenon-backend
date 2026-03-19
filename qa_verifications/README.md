# QA Verifications

This folder has three QA runners with one simple operating pattern:

1. Run the runner script from `tenon-backend/`.
2. The runner overwrites its `*_qa_latest/` folder.
3. Each `*_qa_latest/` directory contains exactly:
   - one report markdown file
   - one `artifacts/` directory

## Run Commands

1. API endpoints QA  
   `./qa_verifications/API-Endpoints-QA/run_api_qa.sh`
2. Database protocol QA  
   `./qa_verifications/Database-Protocol-QA/run_db_protocol_qa.sh`
3. Service logic QA  
   `./qa_verifications/Service-Logic-QA/run-service-logic-qa.sh`

All runners support `--help` for optional flags.

## Uniform Artifact Contract

Each QA type now guarantees:

- `<type>_qa_report.md`: run summary with sections `Run Summary`, `Artifact Layout`, `Step Results`, `Timing`, `Failures`
- `artifacts/`: all generated logs and QA-specific artifacts

Domain-specific artifacts remain under the same `*_qa_latest/` folder:

- API endpoints QA report: `api_endpoints_qa_report.md`
  API artifacts: `artifacts/logs/`, `artifacts/newman_report.json`, optional `artifacts/newman_report.html`
- Database protocol QA report: `db_protocol_qa_report.md`
  Database artifacts: `artifacts/logs/`, `artifacts/sql/`, `artifacts/negative-checks.md`
- Service logic QA report: `service_logic_qa_report.md`
  Service artifacts: `artifacts/logs/`, `artifacts/coverage-existing.json`, optional `artifacts/coverage-combined.json`, `artifacts/strict-validation.txt`
