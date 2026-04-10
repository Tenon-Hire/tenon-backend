# helper import baseline for restructure-compat
import base64
import io
import zipfile
from datetime import UTC, datetime

from app.integrations.github import (
    GithubClient,
    GithubError,
    WorkflowRun,
    template_health,
)
from app.integrations.github.template_health import (
    _decode_contents,
    check_template_health,
    workflow_contract_errors,
)
from app.tasks.services.tasks_services_tasks_template_catalog_constants import (
    TEMPLATE_CATALOG,
)


class _LiveStubClient(GithubClient):
    def __init__(self, responses):
        super().__init__(base_url="https://api.github.com", token="x")
        self.responses = responses

    async def trigger_workflow_dispatch(self, *a, **k):
        if self.responses.get("dispatch_error"):
            raise self.responses["dispatch_error"]

    async def list_workflow_runs(self, *a, **k):
        if "list_error" in self.responses:
            raise self.responses["list_error"]
        return self.responses.get("runs", [])

    async def list_artifacts(self, *a, **k):
        if "artifact_error" in self.responses:
            raise self.responses["artifact_error"]
        return self.responses.get("artifacts", [])

    async def download_artifact_zip(self, *a, **k):
        if "download_error" in self.responses:
            raise self.responses["download_error"]
        return self.responses.get("zip", b"")


def _make_zip(contents: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, body in contents.items():
            zf.writestr(name, body)
    return buf.getvalue()


def _workflow_file_contents() -> dict[str, str]:
    content = "\n".join(
        [
            "uses: actions/upload-artifact@v4",
            "name: winoe-test-results",
            "path: artifacts/winoe-test-results.json",
        ]
    )
    encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
    return {"content": encoded, "encoding": "base64"}


def _completed_run() -> WorkflowRun:
    return WorkflowRun(
        id=42,
        status="completed",
        conclusion="success",
        html_url="https://example.com/run/42",
        head_sha="abc123",
        event="workflow_dispatch",
        created_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    )


__all__ = [name for name in globals() if not name.startswith("__")]
