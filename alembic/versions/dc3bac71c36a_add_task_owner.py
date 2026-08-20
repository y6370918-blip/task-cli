"""add task owner

Revision ID: dc3bac71c36a
Revises: 9c0072d20081
Create Date: 2026-08-12 10:08:59.507530

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dc3bac71c36a'
down_revision: Union[str, Sequence[str], None] = '9c0072d20081'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_users_email"),
        "users",
        ["email"],
        unique=True,
    )

    op.create_index(
        op.f("ix_users_username"),
        "users",
        ["username"],
        unique=True,
    )

    op.add_column(
        "tasks",
        sa.Column(
            "owner_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.create_index(
        op.f("ix_tasks_owner_id"),
        "tasks",
        ["owner_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_tasks_owner_id_users",
        "tasks",
        "users",
        ["owner_id"],
        ["id"],
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_constraint(
        "fk_tasks_owner_id_users",
        "tasks",
        type_="foreignkey",
    )

    op.drop_index(
        op.f("ix_tasks_owner_id"),
        table_name="tasks",
    )

    op.drop_column(
        "tasks",
        "owner_id",
    )

    op.drop_index(
        op.f("ix_users_username"),
        table_name="users",
    )

    op.drop_index(
        op.f("ix_users_email"),
        table_name="users",
    )

    op.drop_table(
        "users"
    )
    # ### end Alembic commands ###
