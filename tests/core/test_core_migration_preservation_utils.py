from __future__ import annotations

import ast
from pathlib import Path

PACKAGE_MARKER_FILES = {
    "app/core/__init__.py",
    "app/core/db/__init__.py",
    "app/core/db/migrations/__init__.py",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_core_package_is_reserved_for_migration_helpers_only():
    repo_root = _repo_root()
    app_core = repo_root / "app" / "core"
    python_files = sorted(
        path.relative_to(repo_root).as_posix() for path in app_core.rglob("*.py")
    )

    assert PACKAGE_MARKER_FILES.issubset(set(python_files))

    violations = [
        rel_path
        for rel_path in python_files
        if rel_path not in PACKAGE_MARKER_FILES
        and not rel_path.startswith("app/core/db/migrations/")
    ]
    assert not violations, f"Non-migration files found under app/core: {violations}"


def test_non_migration_modules_do_not_import_app_core_namespace():
    repo_root = _repo_root()
    violations: list[str] = []
    for source_path in repo_root.rglob("*.py"):
        rel_path = source_path.relative_to(repo_root).as_posix()
        if rel_path.startswith("app/core/db/migrations/") or rel_path.startswith(
            "alembic/versions/"
        ):
            continue
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=rel_path)
        if _imports_app_core(tree):
            violations.append(rel_path)

    assert (
        not violations
    ), f"Unexpected app.core imports outside migration paths: {violations}"


def _imports_app_core(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for imported_alias in node.names:
                if imported_alias.name == "app.core" or imported_alias.name.startswith(
                    "app.core."
                ):
                    return True
        if isinstance(node, ast.ImportFrom) and (
            node.module == "app.core"
            or (isinstance(node.module, str) and node.module.startswith("app.core."))
        ):
            return True
    return False
