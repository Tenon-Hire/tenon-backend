"""Update template repos to Tenon naming

Revision ID: 202504010002
Revises: 202504010001
Create Date: 2025-04-01 00:00:02.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "202504010002"
down_revision: Union[str, Sequence[str], None] = "202504010001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    new_repos = [
        "tenon-dev/tenon-template-python-fastapi",
        "tenon-dev/tenon-template-node-express-ts",
        "tenon-dev/tenon-template-node-nest-ts",
        "tenon-dev/tenon-template-java-springboot",
        "tenon-dev/tenon-template-go-gin",
        "tenon-dev/tenon-template-dotnet-webapi",
        "tenon-dev/tenon-template-monorepo-nextjs-nest",
        "tenon-dev/tenon-template-monorepo-nextjs-fastapi",
        "tenon-dev/tenon-template-monorepo-react-express",
        "tenon-dev/tenon-template-monorepo-react-springboot",
        "tenon-dev/tenon-template-monorepo-expo-fastapi",
        "tenon-dev/tenon-template-mobile-backend-fastapi",
        "tenon-dev/tenon-template-ml-backend-fastapi",
        "tenon-dev/tenon-template-ml-infra-mlops",
    ]
    legacy_brand = "simu" + "hire"
    replacements = [
        (repo.replace("tenon", legacy_brand), repo) for repo in new_repos
    ]

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


def downgrade() -> None:
    conn = op.get_bind()
    new_repos = [
        "tenon-dev/tenon-template-python-fastapi",
        "tenon-dev/tenon-template-node-express-ts",
        "tenon-dev/tenon-template-node-nest-ts",
        "tenon-dev/tenon-template-java-springboot",
        "tenon-dev/tenon-template-go-gin",
        "tenon-dev/tenon-template-dotnet-webapi",
        "tenon-dev/tenon-template-monorepo-nextjs-nest",
        "tenon-dev/tenon-template-monorepo-nextjs-fastapi",
        "tenon-dev/tenon-template-monorepo-react-express",
        "tenon-dev/tenon-template-monorepo-react-springboot",
        "tenon-dev/tenon-template-monorepo-expo-fastapi",
        "tenon-dev/tenon-template-mobile-backend-fastapi",
        "tenon-dev/tenon-template-ml-backend-fastapi",
        "tenon-dev/tenon-template-ml-infra-mlops",
    ]
    legacy_brand = "simu" + "hire"
    replacements = [
        (repo.replace("tenon", legacy_brand), repo) for repo in new_repos
    ]

    for old, new in replacements:
        conn.execute(
            sa.text(
                """
                UPDATE tasks
                SET template_repo = :old
                WHERE template_repo = :new
                """
            ),
            {"new": new, "old": old},
        )
        conn.execute(
            sa.text(
                """
                UPDATE workspaces
                SET template_repo_full_name = :old
                WHERE template_repo_full_name = :new
                """
            ),
            {"new": new, "old": old},
        )
