# System Overview

This file is the canonical documentation index for the Tenon backend.

## Canonical Architecture Docs

- [Architecture Overview](architecture_overview.md)
- [Data Model Relationships](data_model_relationships.md)
- [Simulation Lifecycle](simulation_lifecycle.md)
- [GitHub Integration](github_integration.md)
- [AI Evaluation and Jobs Integration](ai_evaluation_jobs_integration.md)

## API and Runtime Reference

- [API Reference](api.md)
- [README](../README.md)

## Generated Truth Artifacts

- OpenAPI snapshot: `code-quality/documentation/latest/artifacts/openapi_snapshot.json`
- Endpoint matrix: `code-quality/documentation/latest/artifacts/api_endpoint_matrix.md`
- Docs inventory: `code-quality/documentation/latest/artifacts/docs_inventory.md`
- Environment inventory: `code-quality/documentation/latest/artifacts/env_inventory.md`
- Docstring audit: `code-quality/documentation/latest/artifacts/docstring_audit.json`

## QA Documentation

- [QA Verifications README](../qa_verifications/README.md)
- API QA latest report: `qa_verifications/API-Endpoints-QA/api_qa_latest/api_endpoints_qa_report.md`
- DB protocol QA latest report: `qa_verifications/Database-Protocol-QA/db_protocol_qa_latest/db_protocol_qa_report.md`
- Service logic QA latest report: `qa_verifications/Service-Logic-QA/service_logic_qa_latest/service_logic_qa_report.md`

## Maintenance Workflow

1. Export fresh API + endpoint matrix:
   - `poetry run python code-quality/documentation/scripts/docs_api_export.py --strict --verify-doc README.md docs/api.md`
2. Recompute environment parity:
   - `poetry run python code-quality/documentation/scripts/docs_env_inventory.py --strict --markdown-output code-quality/documentation/latest/artifacts/env_inventory.md`
3. Recompute docs inventory + link checks:
   - `poetry run python code-quality/documentation/scripts/docs_inventory.py --strict --markdown-output code-quality/documentation/latest/artifacts/docs_inventory.md`
4. Recompute docstring coverage:
   - `poetry run python code-quality/documentation/scripts/docs_docstring_audit.py --include-module-docs --strict --json > code-quality/documentation/latest/artifacts/docstring_audit.json`
