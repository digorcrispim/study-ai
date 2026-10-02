"""Baseline representando o estado do banco v2.4

Esta migration baseline representa o estado atual do banco de dados
Study AI v2.4, que foi criado manualmente (sem Alembic) e não possui
histórico de migrations aplicado no projeto.

Esta baseline NÃO deve ser executada no banco de dados existente.
Ela serve apenas como ponto de partida para o histórico do Alembic,
permitindo que revisões futuras (como 0002_add_database_indexes)
sejam aplicadas de forma incremental.

Para usar esta baseline em um banco já existente, marcar com:
    alembic stamp 0001_baseline_v24

Revision ID: 0001_baseline_v24
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_baseline_v24"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Cria todas as tabelas no estado do banco v2.4 (baseline)."""
    op.create_table(
        "materials",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "questions",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("material_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("options", postgresql.JSONB(), nullable=False),
        sa.Column("correct_answer", sa.Integer(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("topics", sa.ARRAY(sa.String()), nullable=True),
        sa.Column("difficulty", sa.String(20), nullable=True),
        sa.Column("embedding", Vector(768), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["material_id"],
            ["materials.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "user_answers",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("question_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("selected_answer", sa.Integer(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column(
            "answered_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["questions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "study_sessions",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("material_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_questions", sa.Integer(), nullable=False),
        sa.Column("correct_answers", sa.Integer(), nullable=False),
        sa.Column("accuracy", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(
            ["material_id"],
            ["materials.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_study_sessions_material_id",
        "study_sessions",
        ["material_id"],
    )
    op.create_index(
        "ix_study_sessions_started_at",
        "study_sessions",
        ["started_at"],
    )
    op.create_index(
        "ix_study_sessions_user_id",
        "study_sessions",
        ["user_id"],
    )


def downgrade() -> None:
    """Remove todas as tabelas (reverte baseline)."""
    op.drop_index("ix_study_sessions_user_id", table_name="study_sessions")
    op.drop_index("ix_study_sessions_started_at", table_name="study_sessions")
    op.drop_index("ix_study_sessions_material_id", table_name="study_sessions")
    op.drop_table("study_sessions")
    op.drop_table("user_answers")
    op.drop_table("questions")
    op.drop_table("materials")
