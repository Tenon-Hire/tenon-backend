"""Update template repos to tenon-hire-dev org

Revision ID: 202505200001
Revises: 202505050002
Create Date: 2025-05-20 00:00:01.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "202505200001"
down_revision: Union[str, Sequence[str], None] = "202505050002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TEMPLATES = [
    "tenon-template-monorepo-nextjs-nest",
    "tenon-template-monorepo-nextjs-fastapi",
    "tenon-template-mobile-backend-fastapi",
    "tenon-template-monorepo-react-express",
    "tenon-template-ml-backend-fastapi",
    "tenon-template-ml-infra-mlops",
    "tenon-template-monorepo-react-springboot",
    "tenon-template-monorepo-expo-fastapi",
    "tenon-template-dotnet-webapi",
    "tenon-template-java-springboot",
    "tenon-template-node-express-ts",
    "tenon-template-go-gin",
    "tenon-template-python-fastapi",
    "tenon-template-node-nest-ts",
]


def _run_replacements(conn, replacements: list[tuple[str, str]]) -> None:
    for old, new in replacements:
        conn.execute(
            sa.text(
                """
                UPDATE tasks
                SET template_repo = :new
                WHERE template_repo = :old
                """
            ),
            {"new": new, "old": old},
        )
        conn.execute(
            sa.text(
                """
                UPDATE workspaces
                SET template_repo_full_name = :new
                WHERE template_repo_full_name = :old
                """
            ),
            {"new": new, "old": old},
        )


def upgrade() -> None:
    conn = op.get_bind()
    replacements = [
        (f"tenon-dev/{name}", f"tenon-hire-dev/{name}") for name in _TEMPLATES
    ]
    _run_replacements(conn, replacements)


def downgrade() -> None:
    conn = op.get_bind()
    replacements = [
        (f"tenon-hire-dev/{name}", f"tenon-dev/{name}") for name in _TEMPLATES
    ]
    _run_replacements(conn, replacements)
