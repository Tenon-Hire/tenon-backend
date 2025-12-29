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
    "python-fastapi": "simuhire-dev/simuhire-template-python-fastapi",
    "node-express-ts": "simuhire-dev/simuhire-template-node-express-ts",
    "node-nest-ts": "simuhire-dev/simuhire-template-node-nest-ts",
    "java-springboot": "simuhire-dev/simuhire-template-java-springboot",
    "go-gin": "simuhire-dev/simuhire-template-go-gin",
    "dotnet-webapi": "simuhire-dev/simuhire-template-dotnet-webapi",
    # Web full-stack monorepos
    "monorepo-nextjs-nest": "simuhire-dev/simuhire-template-monorepo-nextjs-nest",
    "monorepo-nextjs-fastapi": "simuhire-dev/simuhire-template-monorepo-nextjs-fastapi",
    "monorepo-react-express": "simuhire-dev/simuhire-template-monorepo-react-express",
    "monorepo-react-springboot": "simuhire-dev/simuhire-template-monorepo-react-springboot",
    # Mobile
    "mobile-fullstack-expo-fastapi": "simuhire-dev/simuhire-template-monorepo-expo-fastapi",
    "mobile-backend-fastapi": "simuhire-dev/simuhire-template-mobile-backend-fastapi",
    # ML
    "ml-backend-fastapi": "simuhire-dev/simuhire-template-ml-backend-fastapi",
    "ml-infra-mlops": "simuhire-dev/simuhire-template-ml-infra-mlops",
}

BAD_TEMPLATE_REPOS = (
    "simuhire-templates/node-day2-api",
    "simuhire-templates/node-day3-debug",
    "simuhire-dev/simuhire-template-python",
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
