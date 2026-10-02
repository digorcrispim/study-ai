"""Testes de metadata para validar os models LearningPlan e
LearningPlanItem do incremento P1.

Estes testes não tocam no banco de dados — validam apenas a estrutura
dos modelos (Base.metadata) e a migration Alembic correspondente.
"""

import importlib
import inspect
import unittest

from sqlalchemy import inspection

from backend.models.entities import Base, LearningPlan, LearningPlanItem


class TestLearningPlanMetadata(unittest.TestCase):
    def test_registered_in_metadata(self):
        self.assertIn("learning_plans", Base.metadata.tables)

    def test_required_columns(self):
        table = Base.metadata.tables["learning_plans"]
        expected_columns = {
            "id",
            "user_id",
            "status",
            "created_at",
            "updated_at",
        }
        self.assertEqual(
            {c.name for c in table.columns},
            expected_columns,
        )

    def test_status_default(self):
        table = Base.metadata.tables["learning_plans"]
        status_col = table.columns["status"]
        self.assertIsNotNone(status_col.default)
        self.assertEqual(status_col.default.arg, "active")

    def test_primary_key(self):
        table = Base.metadata.tables["learning_plans"]
        self.assertEqual(
            [col.name for col in table.primary_key],
            ["id"],
        )


class TestLearningPlanItemMetadata(unittest.TestCase):
    def test_registered_in_metadata(self):
        self.assertIn("learning_plan_items", Base.metadata.tables)

    def test_required_columns(self):
        table = Base.metadata.tables["learning_plan_items"]
        expected_columns = {
            "id",
            "learning_plan_id",
            "topic",
            "material_id",
            "action",
            "priority",
            "status",
            "accuracy_snapshot",
            "total_answers_snapshot",
            "reason",
            "created_at",
            "completed_at",
        }
        self.assertEqual(
            {c.name for c in table.columns},
            expected_columns,
        )

    def test_foreign_key_to_learning_plans(self):
        table = Base.metadata.tables["learning_plan_items"]
        fk = next(
            fk
            for fk in table.foreign_keys
            if fk.parent.name == "learning_plan_id"
        )
        self.assertEqual(fk.column.table.name, "learning_plans")
        self.assertEqual(fk.column.name, "id")

    def test_status_default(self):
        table = Base.metadata.tables["learning_plan_items"]
        status_col = table.columns["status"]
        self.assertIsNotNone(status_col.default)
        self.assertEqual(status_col.default.arg, "pending")

    def test_primary_key(self):
        table = Base.metadata.tables["learning_plan_items"]
        self.assertEqual(
            [col.name for col in table.primary_key],
            ["id"],
        )


class TestBidirectionalRelationship(unittest.TestCase):
    def test_plan_has_items_relationship(self):
        mapper = inspection.inspect(LearningPlan)
        self.assertIn("items", mapper.relationships)

    def test_item_has_plan_relationship(self):
        mapper = inspection.inspect(LearningPlanItem)
        self.assertIn("plan", mapper.relationships)

    def test_back_populates_configured(self):
        plan_mapper = inspection.inspect(LearningPlan)
        item_mapper = inspection.inspect(LearningPlanItem)

        plan_rel = plan_mapper.relationships["items"]
        item_rel = item_mapper.relationships["plan"]

        self.assertEqual(plan_rel.back_populates, "plan")
        self.assertEqual(item_rel.back_populates, "items")

    def test_cascade_delete_orphan(self):
        plan_mapper = inspection.inspect(LearningPlan)
        plan_rel = plan_mapper.relationships["items"]
        self.assertIn("delete", plan_rel.cascade)
        self.assertIn("delete-orphan", plan_rel.cascade)


class TestMigrationP1(unittest.TestCase):
    """Valida a migration P1 sem executá-la."""

    def setUp(self):
        self.mod = importlib.import_module(
            "backend.migrations.versions."
            "1768c7f91fe6_add_learning_plan_persistence_tables"
        )
        self.source = inspect.getsource(self.mod)

    def test_revision_id(self):
        self.assertEqual(self.mod.revision, "1768c7f91fe6")

    def test_down_revision(self):
        self.assertEqual(
            self.mod.down_revision,
            "0002_add_database_indexes",
        )

    def test_upgrade_creates_only_two_tables(self):
        upgrade_source = self.source.split("def downgrade")[0]
        self.assertIn('"learning_plans"', upgrade_source)
        self.assertIn('"learning_plan_items"', upgrade_source)
        # Não deve criar ou alterar tabelas existentes
        for existing in [
            "materials",
            "questions",
            "user_answers",
            "study_sessions",
        ]:
            self.assertNotIn(
                f'"{existing}"',
                upgrade_source,
                f"upgrade() não deve referenciar tabela {existing}.",
            )

    def test_upgrade_does_not_touch_existing_indexes(self):
        upgrade_source = self.source.split("def downgrade")[0]
        for index in [
            "ix_questions_material_id_difficulty",
            "ix_user_answers_user_id_answered_at",
            "ix_user_answers_user_id_question_id_answered_at",
            "ix_study_sessions_material_id",
            "ix_study_sessions_started_at",
            "ix_study_sessions_user_id_started_at",
            "ix_study_sessions_user_id",
        ]:
            self.assertNotIn(
                index,
                upgrade_source,
                f"upgrade() não deve tocar o índice {index}.",
            )

    def test_downgrade_removes_only_two_tables(self):
        downgrade_source = self.source.split("def downgrade")[1]
        self.assertIn('"learning_plan_items"', downgrade_source)
        self.assertIn('"learning_plans"', downgrade_source)
        for existing in [
            "materials",
            "questions",
            "user_answers",
            "study_sessions",
        ]:
            self.assertNotIn(
                f'"{existing}"',
                downgrade_source,
                f"downgrade() não deve remover tabela {existing}.",
            )


if __name__ == "__main__":
    unittest.main()
