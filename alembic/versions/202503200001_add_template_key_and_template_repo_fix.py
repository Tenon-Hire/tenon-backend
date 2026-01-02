"""Add simulation.template_key and fix template_repo defaults

Revision ID: 202503200001
Revises: sg2893ihjsdfknqu
Create Date: 2025-03-20 00:00:01.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "202503200001"
down_revision: Union[str, Sequence[str], None] = "sg2893ihjsdfknqu"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_TEMPLATE_KEY = "python-fastapi"

TEMPLATE_REPOS = {
    # Backend-only templates
    "python-fastapi": "tenon-dev/tenon-template-python-fastapi",
    "node-express-ts": "tenon-dev/tenon-template-node-express-ts",
    "node-nest-ts": "tenon-dev/tenon-template-node-nest-ts",
    "java-springboot": "tenon-dev/tenon-template-java-springboot",
    "go-gin": "tenon-dev/tenon-template-go-gin",
    "dotnet-webapi": "tenon-dev/tenon-template-dotnet-webapi",
    # Web full-stack monorepos
    "monorepo-nextjs-nest": "tenon-dev/tenon-template-monorepo-nextjs-nest",
    "monorepo-nextjs-fastapi": "tenon-dev/tenon-template-monorepo-nextjs-fastapi",
    "monorepo-react-express": "tenon-dev/tenon-template-monorepo-react-express",
    "monorepo-react-springboot": "tenon-dev/tenon-template-monorepo-react-springboot",
    # Mobile
    "mobile-fullstack-expo-fastapi": "tenon-dev/tenon-template-monorepo-expo-fastapi",
    "mobile-backend-fastapi": "tenon-dev/tenon-template-mobile-backend-fastapi",
    # ML
    "ml-backend-fastapi": "tenon-dev/tenon-template-ml-backend-fastapi",
    "ml-infra-mlops": "tenon-dev/tenon-template-ml-infra-mlops",
}

BAD_TEMPLATE_REPOS = (
    "tenon-templates/node-day2-api",
    "tenon-templates/node-day3-debug",
    "tenon-dev/tenon-template-python",
)


def upgrade() -> None:
    op.add_column(
        "simulations",
        sa.Column(
            "template_key",
            sa.String(length=255),
            nullable=False,
            server_default=DEFAULT_TEMPLATE_KEY,
        ),
    )
    op.create_index(
        "ix_simulations_template_key", "simulations", ["template_key"], unique=False
    )

    default_repo = TEMPLATE_REPOS[DEFAULT_TEMPLATE_KEY]
    case_clauses = " ".join(
        f"WHEN s.template_key = '{key}' THEN '{repo}'"
        for key, repo in TEMPLATE_REPOS.items()
    )
    repo_case = f"(CASE {case_clauses} ELSE '{default_repo}' END)"
    bad_values_sql = ", ".join(f"'{val}'" for val in BAD_TEMPLATE_REPOS)

    op.execute(
        sa.text(
            f"""
            UPDATE tasks AS t
            SET template_repo = {repo_case}
            FROM simulations AS s
            WHERE t.simulation_id = s.id
              AND t.type IN ('code', 'debug')
              AND t.day_index IN (2, 3)
              AND (
                t.template_repo IS NULL
                OR trim(t.template_repo) = ''
                OR t.template_repo IN ({bad_values_sql})
              )
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_simulations_template_key", table_name="simulations")
    op.drop_column("simulations", "template_key")
