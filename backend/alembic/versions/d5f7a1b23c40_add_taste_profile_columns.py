"""add taste profile columns to user_preferences

Revision ID: d5f7a1b23c40
Revises: c4e8f2a31b09
Create Date: 2026-03-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "d5f7a1b23c40"
down_revision: Union[str, None] = "c4e8f2a31b09"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user_preferences", sa.Column("taste_profile", sa.Text(), nullable=True))
    op.add_column("user_preferences", sa.Column("taste_profile_raw", sa.Text(), nullable=True))
    op.add_column("user_preferences", sa.Column("taste_profile_updated_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("user_preferences", "taste_profile_updated_at")
    op.drop_column("user_preferences", "taste_profile_raw")
    op.drop_column("user_preferences", "taste_profile")
