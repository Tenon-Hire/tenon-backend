"""Application module for tasks services tasks template catalog constants workflows."""

from __future__ import annotations

from typing import Any

DEFAULT_TEMPLATE_KEY = "python-fastapi"
CATALOG_ENTRIES: list[tuple[str, str, str]] = [
    (
        "python-fastapi",
        "winoe-ai-repos/winoe-ai-template-python-fastapi",
        "Python (FastAPI)",
    ),
    (
        "node-express-ts",
        "winoe-ai-repos/winoe-ai-template-node-express-ts",
        "Node.js (Express, TS)",
    ),
    (
        "node-nest-ts",
        "winoe-ai-repos/winoe-ai-template-node-nest-ts",
        "Node.js (NestJS, TS)",
    ),
    (
        "java-springboot",
        "winoe-ai-repos/winoe-ai-template-java-springboot",
        "Java (Spring Boot)",
    ),
    ("go-gin", "winoe-ai-repos/winoe-ai-template-go-gin", "Go (Gin)"),
    (
        "dotnet-webapi",
        "winoe-ai-repos/winoe-ai-template-dotnet-webapi",
        ".NET (Web API)",
    ),
    (
        "monorepo-nextjs-nest",
        "winoe-ai-repos/winoe-ai-template-monorepo-nextjs-nest",
        "Monorepo (Next.js + NestJS)",
    ),
    (
        "monorepo-nextjs-fastapi",
        "winoe-ai-repos/winoe-ai-template-monorepo-nextjs-fastapi",
        "Monorepo (Next.js + FastAPI)",
    ),
    (
        "monorepo-react-express",
        "winoe-ai-repos/winoe-ai-template-monorepo-react-express",
        "Monorepo (React + Express)",
    ),
    (
        "monorepo-react-springboot",
        "winoe-ai-repos/winoe-ai-template-monorepo-react-springboot",
        "Monorepo (React + Spring Boot)",
    ),
    (
        "mobile-fullstack-expo-fastapi",
        "winoe-ai-repos/winoe-ai-template-monorepo-expo-fastapi",
        "Mobile Fullstack (Expo + FastAPI)",
    ),
    (
        "mobile-backend-fastapi",
        "winoe-ai-repos/winoe-ai-template-mobile-backend-fastapi",
        "Mobile Backend (FastAPI)",
    ),
    (
        "ml-backend-fastapi",
        "winoe-ai-repos/winoe-ai-template-ml-backend-fastapi",
        "ML Backend (FastAPI)",
    ),
    (
        "ml-infra-mlops",
        "winoe-ai-repos/winoe-ai-template-ml-infra-mlops",
        "ML Infra / MLOps",
    ),
]

TEMPLATE_CATALOG: dict[str, dict[str, Any]] = {
    key: {"repo_full_name": repo_full_name, "display_name": display_name}
    for key, repo_full_name, display_name in CATALOG_ENTRIES
}
ALLOWED_TEMPLATE_KEYS: set[str] = set(TEMPLATE_CATALOG.keys())


def _legacy_repo_name(repo_full_name: str, owner: str) -> str:
    legacy_repo = repo_full_name.split("/", 1)[1].replace(
        "winoe-ai-template-", "winoe-template-", 1
    )
    return f"{owner}/{legacy_repo}"


LEGACY_TEMPLATE_REPO_REWRITES: dict[str, str] = {
    _legacy_repo_name(repo_full_name, owner): repo_full_name
    for owner in ("winoe-ai-repos", "winoe-hire-dev")
    for _, repo_full_name, _ in CATALOG_ENTRIES
    if repo_full_name.startswith("winoe-ai-repos/winoe-ai-template-")
}
LEGACY_TEMPLATE_REPO_REWRITES.update(
    {
        "winoe-templates/node-day2-api": TEMPLATE_CATALOG[DEFAULT_TEMPLATE_KEY][
            "repo_full_name"
        ],
        "winoe-templates/node-day3-debug": TEMPLATE_CATALOG[DEFAULT_TEMPLATE_KEY][
            "repo_full_name"
        ],
        "winoe-dev/winoe-template-python": TEMPLATE_CATALOG["python-fastapi"][
            "repo_full_name"
        ],
    }
)

__all__ = [
    "DEFAULT_TEMPLATE_KEY",
    "CATALOG_ENTRIES",
    "TEMPLATE_CATALOG",
    "ALLOWED_TEMPLATE_KEYS",
    "LEGACY_TEMPLATE_REPO_REWRITES",
]
