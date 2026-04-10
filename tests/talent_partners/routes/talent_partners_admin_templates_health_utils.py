import base64
import io
import zipfile
from datetime import UTC, datetime

from app.integrations.github import GithubError, WorkflowRun


class MissingWorkflowGithubClient:
    async def get_repo(self, repo_full_name: str):
        return {"default_branch": "main"}

    async def get_branch(self, repo_full_name: str, branch: str):
        return {"commit": {"sha": "abc123"}}

    async def get_file_contents(
        self, repo_full_name: str, file_path: str, *, ref: str | None = None
    ):
        raise GithubError("not found", status_code=404)


def make_zip(contents: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, body in contents.items():
            zf.writestr(name, body)
    return buf.getvalue()


def workflow_file_contents() -> dict[str, str]:
    content = "\n".join(
        [
            "uses: actions/upload-artifact@v4",
            "name: winoe-test-results",
            "path: artifacts/winoe-test-results.json",
        ]
    )
    encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
    return {"content": encoded, "encoding": "base64"}


def completed_run() -> WorkflowRun:
    return WorkflowRun(
        id=42,
        status="completed",
        conclusion="success",
        html_url="https://example.com/run/42",
        head_sha="abc123",
        event="workflow_dispatch",
        created_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    )


class LiveGithubClient:
    async def get_repo(self, repo_full_name: str):
        return {"default_branch": "main"}

    async def get_branch(self, repo_full_name: str, branch: str):
        return {"commit": {"sha": "abc123"}}

    async def get_file_contents(
        self, repo_full_name: str, file_path: str, *, ref: str | None = None
    ):
        return workflow_file_contents()

    async def trigger_workflow_dispatch(self, *args, **kwargs):
        return None

    async def list_workflow_runs(self, *args, **kwargs):
        return [completed_run()]

    async def list_artifacts(self, *args, **kwargs):
        return [{"id": 1, "name": "winoe-test-results", "expired": False}]

    async def download_artifact_zip(self, *args, **kwargs):
        body = '{"passed": 1, "failed": 0, "total": 1, "stdout": "", "stderr": ""}'
        return make_zip({"winoe-test-results.json": body})
