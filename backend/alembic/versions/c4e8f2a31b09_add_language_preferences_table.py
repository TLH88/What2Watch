"""add language_preferences table

Revision ID: c4e8f2a31b09
Revises: 37a963ac4704
Create Date: 2026-03-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c4e8f2a31b09"
down_revision: Union[str, None] = "37a963ac4704"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "language_preferences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("language_code", sa.String(10), nullable=False),
        sa.Column("language_name", sa.String(100), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("language_preferences")
