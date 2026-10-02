"""Adiciona índices de banco alinhados às consultas reais

Revisão aditiva que cria índices compostos e simples coerentes
com as consultas reais identificadas no sistema, sem alterar
campos, relacionamentos, tipos ou lógica de negócio.

Índices criados:
  - questions: ix_questions_material_id_difficulty (material_id, difficulty)
  - user_answers: ix_user_answers_user_id_answered_at (user_id, answered_at)
  - user_answers: ix_user_answers_user_id_question_id_answered_at
      (user_id, question_id, answered_at)
  - study_sessions: ix_study_sessions_user_id_started_at (user_id, started_at)

Índices preservados do v2.4 (não alterados):
  - study_sessions: ix_study_sessions_material_id (material_id)
  - study_sessions: ix_study_sessions_started_at (started_at)

Índice removido:
  - study_sessions: ix_study_sessions_user_id (user_id)
    Removido por ser redundante: o índice composto (user_id, started_at)
    cobre buscas por user_id sozinho (prefixo esquerdo).

Justificativa:
  - questions (material_id, difficulty): consulta adaptativa que filtra
    por material_id e difficulty simultaneamente.
  - user_answers (user_id, answered_at): listagem de respostas do usuário
    ordenada por answered_at.
  - user_answers (user_id, question_id, answered_at): consulta de revisão
    que filtra por user_id e um conjunto de question_ids, ordenada por
    question_id e answered_at.
  - study_sessions (user_id, started_at): listagem de sessões do usuário
    ordenada por started_at. O índice composto cobre buscas por user_id
    sozinho (prefixo esquerdo), tornando o índice simples em user_id
    redundante — por isso ele é removido nesta revisão.
  - study_sessions (material_id, started_at): já existiam no v2.4 e
    são preservados intactos.

ESTA MIGRATION DEVE SER APLICADA MANUALMENTE PELO ADMINISTRADOR.
NÃO execute alembic upgrade head automaticamente.

Revision ID: 0002_add_database_indexes
Revises: 0001_baseline_v24
Create Date: 2025-01-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_add_database_indexes"
down_revision: Union[str, Sequence[str], None] = "0001_baseline_v24"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Cria índices novos e remove índice redundante do v2.4."""
    # Remove índice simples redundante: o composto (user_id, started_at)
    # cobre buscas por user_id sozinho (prefixo esquerdo).
    op.drop_index(
        "ix_study_sessions_user_id",
        table_name="study_sessions",
    )

    # Cria os índices novos que não existiam no v2.4.
    op.create_index(
        "ix_questions_material_id_difficulty",
        "questions",
        ["material_id", "difficulty"],
    )
    op.create_index(
        "ix_user_answers_user_id_answered_at",
        "user_answers",
        ["user_id", "answered_at"],
    )
    op.create_index(
        "ix_user_answers_user_id_question_id_answered_at",
        "user_answers",
        ["user_id", "question_id", "answered_at"],
    )
    op.create_index(
        "ix_study_sessions_user_id_started_at",
        "study_sessions",
        ["user_id", "started_at"],
    )


def downgrade() -> None:
    """Reverte a evolução: remove índices novos e recria o redundante."""
    op.drop_index(
        "ix_study_sessions_user_id_started_at",
        table_name="study_sessions",
    )
    op.drop_index(
        "ix_user_answers_user_id_question_id_answered_at",
        table_name="user_answers",
    )
    op.drop_index(
        "ix_user_answers_user_id_answered_at",
        table_name="user_answers",
    )
    op.drop_index(
        "ix_questions_material_id_difficulty",
        table_name="questions",
    )

    # Recria o índice simples redundante removido no upgrade.
    op.create_index(
        "ix_study_sessions_user_id",
        "study_sessions",
        ["user_id"],
    )
