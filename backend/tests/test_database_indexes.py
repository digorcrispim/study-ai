"""Testes de metadata para garantir que os índices esperados
estão declarados nas entidades SQLAlchemy.

Estes testes não tocam no banco de dados — validam apenas a estrutura
dos modelos (Base.metadata), garantindo que os índices declarados
nas entidades correspondem ao estado desejado após o Bloco 3B.

Estado desejado:

questions:
  - PK
  - ix_questions_material_id_difficulty (material_id, difficulty)

user_answers:
  - PK
  - ix_user_answers_user_id_answered_at (user_id, answered_at)
  - ix_user_answers_user_id_question_id_answered_at
      (user_id, question_id, answered_at)

study_sessions:
  - PK
  - ix_study_sessions_material_id (material_id)
  - ix_study_sessions_started_at (started_at)
  - ix_study_sessions_user_id_started_at (user_id, started_at)
"""

import unittest

from backend.models.entities import (
    Question,
    StudySession,
    UserAnswer,
)


def get_table_indexes(table):
    """Retorna um dict {nome_do_indice: [colunas]} dos índices da tabela."""
    return {
        idx.name: [col.name for col in idx.columns]
        for idx in table.indexes
    }


class TestQuestionsIndexes(unittest.TestCase):
    def test_has_material_id_difficulty_composite_index(self):
        indexes = get_table_indexes(Question.__table__)
        self.assertIn(
            "ix_questions_material_id_difficulty",
            indexes,
        )
        self.assertEqual(
            indexes["ix_questions_material_id_difficulty"],
            ["material_id", "difficulty"],
        )

    def test_no_unexpected_indexes(self):
        indexes = get_table_indexes(Question.__table__)
        self.assertEqual(
            set(indexes),
            {"ix_questions_material_id_difficulty"},
        )


class TestUserAnswersIndexes(unittest.TestCase):
    def test_has_user_id_answered_at_composite_index(self):
        indexes = get_table_indexes(UserAnswer.__table__)
        self.assertIn(
            "ix_user_answers_user_id_answered_at",
            indexes,
        )
        self.assertEqual(
            indexes["ix_user_answers_user_id_answered_at"],
            ["user_id", "answered_at"],
        )

    def test_has_user_id_question_id_answered_at_composite_index(self):
        indexes = get_table_indexes(UserAnswer.__table__)
        self.assertIn(
            "ix_user_answers_user_id_question_id_answered_at",
            indexes,
        )
        self.assertEqual(
            indexes["ix_user_answers_user_id_question_id_answered_at"],
            ["user_id", "question_id", "answered_at"],
        )

    def test_no_unexpected_indexes(self):
        indexes = get_table_indexes(UserAnswer.__table__)
        self.assertEqual(
            set(indexes),
            {
                "ix_user_answers_user_id_answered_at",
                "ix_user_answers_user_id_question_id_answered_at",
            },
        )


class TestStudySessionsIndexes(unittest.TestCase):
    def test_has_material_id_index(self):
        indexes = get_table_indexes(StudySession.__table__)
        self.assertIn(
            "ix_study_sessions_material_id",
            indexes,
        )
        self.assertEqual(
            indexes["ix_study_sessions_material_id"],
            ["material_id"],
        )

    def test_has_started_at_index(self):
        indexes = get_table_indexes(StudySession.__table__)
        self.assertIn(
            "ix_study_sessions_started_at",
            indexes,
        )
        self.assertEqual(
            indexes["ix_study_sessions_started_at"],
            ["started_at"],
        )

    def test_has_user_id_started_at_composite_index(self):
        indexes = get_table_indexes(StudySession.__table__)
        self.assertIn(
            "ix_study_sessions_user_id_started_at",
            indexes,
        )
        self.assertEqual(
            indexes["ix_study_sessions_user_id_started_at"],
            ["user_id", "started_at"],
        )

    def test_no_redundant_user_id_simple_index(self):
        """O índice composto (user_id, started_at) cobre buscas
        por user_id sozinho, então não deve haver um índice
        simples redundante em user_id."""
        indexes = get_table_indexes(StudySession.__table__)
        simple_user_id_indexes = [
            name
            for name, cols in indexes.items()
            if cols == ["user_id"]
        ]
        self.assertEqual(
            simple_user_id_indexes,
            [],
            "Não deve haver índice simples redundante em user_id "
            "quando o composto (user_id, started_at) existe.",
        )

    def test_no_unexpected_indexes(self):
        indexes = get_table_indexes(StudySession.__table__)
        self.assertEqual(
            set(indexes),
            {
                "ix_study_sessions_material_id",
                "ix_study_sessions_started_at",
                "ix_study_sessions_user_id_started_at",
            },
        )


class TestMigration0002DoesNotTouchStartedAt(unittest.TestCase):
    """Garante que a revisão 0002 não cria nem remove
    ix_study_sessions_started_at, pois esse índice pertence
    à baseline 0001 (estado v2.4) e deve permanecer intacto."""

    def setUp(self):
        import importlib
        import inspect

        mod = importlib.import_module(
            "backend.migrations.versions.0002_add_database_indexes"
        )
        self.source = inspect.getsource(mod)

    def test_upgrade_does_not_create_started_at(self):
        self.assertNotIn(
            '"ix_study_sessions_started_at"',
            self.source.split("def downgrade")[0],
            "0002.upgrade() não deve criar ix_study_sessions_started_at "
            "(pertence à baseline).",
        )

    def test_downgrade_does_not_drop_started_at(self):
        self.assertNotIn(
            '"ix_study_sessions_started_at"',
            self.source.split("def downgrade")[1],
            "0002.downgrade() não deve remover ix_study_sessions_started_at "
            "(pertence à baseline).",
        )


if __name__ == "__main__":
    unittest.main()
