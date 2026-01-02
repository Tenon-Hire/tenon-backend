"""Fix template_repo bad values for code/debug tasks

Revision ID: sg2893ihjsdfknqu
Revises: f3c5e8c2d7ab
"""

from alembic import op
import sqlalchemy as sa

revision = "sg2893ihjsdfknqu"
down_revision = "f3c5e8c2d7ab"
branch_labels = None
depends_on = None

GOOD = "tenon-dev/tenon-template-python"
BAD = (
    "tenon-templates/node-day2-api",
    "tenon-templates/node-day3-debug",
)

def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        op.execute(
            sa.text(
                """
                UPDATE tasks
                SET template_repo = :good
                WHERE type IN ('code','debug')
                  AND day_index IN (2,3)
                  AND (
                    template_repo IS NULL
                    OR trim(template_repo) = ''
                    OR template_repo IN (:bad1, :bad2)
                  )
                """
            ).bindparams(good=GOOD, bad1=BAD[0], bad2=BAD[1])
        )
    else:
        op.execute(
            sa.text(
                """
                UPDATE tasks
                SET template_repo = :good
                WHERE type IN ('code','debug')
                  AND day_index IN (2,3)
                  AND (
                    template_repo IS NULL
                    OR btrim(template_repo) = ''
                    OR template_repo = ANY(:bad)
                  )
                """
            ).bindparams(good=GOOD, bad=list(BAD))
        )

def downgrade() -> None:
    # optional: revert to NULL (safe) or map back to BAD by day_index (but that reintroduces the bug)
    op.execute(
        sa.text(
            """
            UPDATE tasks
            SET template_repo = NULL
            WHERE type IN ('code','debug')
              AND day_index IN (2,3)
              AND template_repo = :good
            """
        ).bindparams(good=GOOD)
    )
