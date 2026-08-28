"""make score history index order explicit

Revision ID: 0002_desc_score_index
Revises: 0001_users_scores
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_desc_score_index"
down_revision = "0001_users_scores"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_score_events_user_created_at", table_name="score_events")
    op.create_index(
        "ix_score_events_user_created_at",
        "score_events",
        ["user_id", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_score_events_user_created_at", table_name="score_events")
    op.create_index(
        "ix_score_events_user_created_at",
        "score_events",
        ["user_id", "created_at"],
    )
