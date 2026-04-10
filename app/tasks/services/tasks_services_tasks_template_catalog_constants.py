"""Application module for tasks services tasks template catalog constants workflows."""

from __future__ import annotations

from typing import Any

DEFAULT_TEMPLATE_KEY = "python-fastapi"
CATALOG_ENTRIES: list[tuple[str, str, str]] = [
    (
        "python-fastapi",
        "winoe-hire-dev/winoe-template-python-fastapi",
        "Python (FastAPI)",
    ),
    (
        "node-express-ts",
        "winoe-hire-dev/winoe-template-node-express-ts",
        "Node.js (Express, TS)",
    ),
    (
        "node-nest-ts",
        "winoe-hire-dev/winoe-template-node-nest-ts",
        "Node.js (NestJS, TS)",
    ),
    (
        "java-springboot",
        "winoe-hire-dev/winoe-template-java-springboot",
        "Java (Spring Boot)",
    ),
    ("go-gin", "winoe-hire-dev/winoe-template-go-gin", "Go (Gin)"),
    ("dotnet-webapi", "winoe-hire-dev/winoe-template-dotnet-webapi", ".NET (Web API)"),
    (
        "monorepo-nextjs-nest",
        "winoe-hire-dev/winoe-template-monorepo-nextjs-nest",
        "Monorepo (Next.js + NestJS)",
    ),
    (
        "monorepo-nextjs-fastapi",
        "winoe-hire-dev/winoe-template-monorepo-nextjs-fastapi",
        "Monorepo (Next.js + FastAPI)",
    ),
    (
        "monorepo-react-express",
        "winoe-hire-dev/winoe-template-monorepo-react-express",
        "Monorepo (React + Express)",
    ),
    (
        "monorepo-react-springboot",
        "winoe-hire-dev/winoe-template-monorepo-react-springboot",
        "Monorepo (React + Spring Boot)",
    ),
    (
        "mobile-fullstack-expo-fastapi",
        "winoe-hire-dev/winoe-template-monorepo-expo-fastapi",
        "Mobile Fullstack (Expo + FastAPI)",
    ),
    (
        "mobile-backend-fastapi",
        "winoe-hire-dev/winoe-template-mobile-backend-fastapi",
        "Mobile Backend (FastAPI)",
    ),
    (
        "ml-backend-fastapi",
        "winoe-hire-dev/winoe-template-ml-backend-fastapi",
        "ML Backend (FastAPI)",
    ),
    (
        "ml-infra-mlops",
        "winoe-hire-dev/winoe-template-ml-infra-mlops",
        "ML Infra / MLOps",
    ),
]

TEMPLATE_CATALOG: dict[str, dict[str, Any]] = {
    key: {"repo_full_name": repo_full_name, "display_name": display_name}
    for key, repo_full_name, display_name in CATALOG_ENTRIES
}
ALLOWED_TEMPLATE_KEYS: set[str] = set(TEMPLATE_CATALOG.keys())
LEGACY_TEMPLATE_REPO_REWRITES: dict[str, str] = {
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

__all__ = [
    "DEFAULT_TEMPLATE_KEY",
    "CATALOG_ENTRIES",
    "TEMPLATE_CATALOG",
    "ALLOWED_TEMPLATE_KEYS",
    "LEGACY_TEMPLATE_REPO_REWRITES",
]
