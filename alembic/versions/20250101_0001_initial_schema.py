import sqlalchemy as sa

from alembic import op

revision = "20250101_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), unique=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200)),
        sa.Column("email", sa.String(255), unique=True, index=True),
        sa.Column("role", sa.String(50)),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id")),
        sa.Column("password_hash", sa.String(255)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    )

    op.create_table(
        "simulations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id")),
        sa.Column("title", sa.String(255)),
        sa.Column("role", sa.String(255)),
        sa.Column("tech_stack", sa.String(255)),
        sa.Column("seniority", sa.String(100)),
        sa.Column("scenario_template", sa.String(255)),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("status", sa.String(50)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    )

    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("simulation_id", sa.Integer(), sa.ForeignKey("simulations.id")),
        sa.Column("day_index", sa.Integer()),
        sa.Column("type", sa.String(50)),
        sa.Column("title", sa.String(255)),
        sa.Column("description", sa.Text()),
        sa.Column("starter_code_path", sa.String(500)),
        sa.Column("test_file_path", sa.String(500)),
        sa.Column("max_score", sa.Integer()),
    )

    op.create_table(
        "candidate_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("simulation_id", sa.Integer(), sa.ForeignKey("simulations.id")),
        sa.Column("candidate_user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("invite_email", sa.String(255)),
        sa.Column("token", sa.String(255), unique=True, index=True),
        sa.Column("status", sa.String(50)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "submissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "candidate_session_id", sa.Integer(), sa.ForeignKey("candidate_sessions.id")
        ),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id")),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("content_text", sa.Text()),
        sa.Column("code_repo_path", sa.String(500)),
        sa.Column("tests_passed", sa.Integer()),
        sa.Column("tests_failed", sa.Integer()),
        sa.Column("test_output", sa.Text()),
    )


def downgrade():
    op.drop_table("submissions")
    op.drop_table("candidate_sessions")
    op.drop_table("tasks")
    op.drop_table("simulations")
    op.drop_table("users")
    op.drop_table("companies")
