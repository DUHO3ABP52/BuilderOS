"""knowledge graph edges

Revision ID: 20260711_0005
Revises: 20260711_0004
Create Date: 2026-07-11
"""

from alembic import op
import sqlalchemy as sa

revision = "20260711_0005"
down_revision = "20260711_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "graph_edges",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("from_type", sa.String(length=32), nullable=False),
        sa.Column("from_id", sa.Uuid(), nullable=False),
        sa.Column("to_type", sa.String(length=32), nullable=False),
        sa.Column("to_id", sa.Uuid(), nullable=False),
        sa.Column("relation", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1"),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="manual"),
        sa.Column("created_by_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("graph_edges")
