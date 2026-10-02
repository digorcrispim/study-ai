"""add learning plan persistence tables

Cria as tabelas learning_plans e learning_plan_items para persistir
o Plano de Aprendizagem. Este é o incremento P1 — somente a estrutura
de banco. A lógica de criação, recalculação e endpoints será tratada
no P2.

Revision ID: 1768c7f91fe6
Revises: 0002_add_database_indexes
Create Date: 2026-10-02 17:04:03.469280

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "1768c7f91fe6"
down_revision: Union[str, Sequence[str], None] = "0002_add_database_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Cria as tabelas learning_plans e learning_plan_items."""
    op.create_table(
        "learning_plans",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "learning_plan_items",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("learning_plan_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("topic", sa.Text(), nullable=False),
        sa.Column("material_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("accuracy_snapshot", sa.Float(), nullable=True),
        sa.Column("total_answers_snapshot", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["learning_plan_id"],
            ["learning_plans.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Remove as tabelas learning_plan_items e learning_plans."""
    op.drop_table("learning_plan_items")
    op.drop_table("learning_plans")
