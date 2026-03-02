from __future__ import annotations

import importlib
from pathlib import Path

import pytest


def _star_export_modules() -> list[str]:
    repo_root = Path(__file__).resolve().parents[2]
    app_root = repo_root / "app"
    modules: list[str] = []
    for path in app_root.rglob("*.py"):
        relative = path.relative_to(app_root)
        if (
            relative.parts[0] in {"domains", "infra"}
            or relative.parts[0] == "api"
            and len(relative.parts) > 1
            and relative.parts[1] == "routes"
        ):
            pass
        else:
            continue
        lines = [
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        if (
            len(lines) == 1
            and lines[0].startswith("from app.")
            and " import *" in lines[0]
        ):
            modules.append(
                f"app.{relative.with_suffix('').as_posix().replace('/', '.')}"
            )
    return sorted(set(modules))


@pytest.mark.parametrize("module_name", _star_export_modules())
def test_star_export_module_imports(module_name: str):
    importlib.import_module(module_name)
