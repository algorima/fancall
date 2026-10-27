"""call_memories table

Revision ID: a7c3d2e91f40
Revises: 81c09e10f965
Create Date: 2026-10-27 23:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7c3d2e91f40"
down_revision: Union[str, None] = "81c09e10f965"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "call_memories",
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("memory_key", sa.String(), nullable=False),
        sa.Column("speaker", sa.String(length=8), nullable=False),
        sa.Column("text", sa.String(length=500), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_call_memories")),
    )
    op.create_index(
        "ix_call_memories_fan_trainee_time",
        "call_memories",
        ["user_id", "memory_key", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_call_memories_fan_trainee_time", table_name="call_memories")
    op.drop_table("call_memories")
