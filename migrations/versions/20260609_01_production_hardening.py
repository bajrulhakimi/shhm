"""Add structured results and persistent scan jobs."""

import sqlalchemy as sa
from alembic import op

revision = "20260609_01"
down_revision = None
branch_labels = None
depends_on = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    tables = _tables()
    if "users" not in tables:
        from app.database import Base
        from app.models import (  # noqa: F401
            analysis,
            scan_job,
            scan_result,
            stock,
            usage,
            user,
            watchlist,
        )

        Base.metadata.create_all(bind=op.get_bind())
        return
    if "analyses" in tables and "structured_result" not in _columns("analyses"):
        op.add_column("analyses", sa.Column("structured_result", sa.JSON(), nullable=True))
    if "scan_results" in tables and "structured_result" not in _columns("scan_results"):
        op.add_column("scan_results", sa.Column("structured_result", sa.JSON(), nullable=True))
    if "scan_jobs" not in tables:
        op.create_table(
            "scan_jobs",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("group_name", sa.String(length=100), nullable=False),
            sa.Column("requested_limit", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("total_stocks", sa.Integer(), nullable=False),
            sa.Column("processed_stocks", sa.Integer(), nullable=False),
            sa.Column("result", sa.JSON(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_scan_jobs_user_id", "scan_jobs", ["user_id"])
        op.create_index("ix_scan_jobs_group_name", "scan_jobs", ["group_name"])
        op.create_index("ix_scan_jobs_status", "scan_jobs", ["status"])


def downgrade() -> None:
    tables = _tables()
    if "scan_jobs" in tables:
        op.drop_table("scan_jobs")
    if "scan_results" in tables and "structured_result" in _columns("scan_results"):
        op.drop_column("scan_results", "structured_result")
    if "analyses" in tables and "structured_result" in _columns("analyses"):
        op.drop_column("analyses", "structured_result")
