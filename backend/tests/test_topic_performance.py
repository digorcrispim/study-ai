import unittest
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.models.entities import Question, UserAnswer
from backend.routers.answers import get_db, router


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class FakeSession:
    def __init__(self):
        self.rows = []
        self.selected_column_sets = []

    def execute(self, statement):
        selected_columns = set(statement.selected_columns.keys())
        self.selected_column_sets.append(selected_columns)
        if selected_columns == {"is_correct", "topics", "material_id"}:
            return FakeResult(
                [
                    (answer.is_correct, question.topics, question.material_id)
                    for answer, question in self.rows
                ]
            )
        return FakeResult(self.rows)


class TopicPerformanceEndpointTests(unittest.TestCase):
    def setUp(self):
        self.db = FakeSession()
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(app)
        self.user_id = uuid4()

    def tearDown(self):
        self.client.close()

    def add_question(self, topics, material_id, answers):
        question = Question(
            id=uuid4(),
            material_id=material_id,
            question_text="Pergunta de teste",
            options={"0": "A"},
            correct_answer=0,
            topics=topics,
            difficulty="easy",
        )

        for is_correct in answers:
            answer = UserAnswer(
                id=uuid4(),
                user_id=self.user_id,
                question_id=question.id,
                selected_answer=0,
                is_correct=is_correct,
            )
            self.db.rows.append((answer, question))

    def get_topics(self):
        response = self.client.get(f"/questions/user/{self.user_id}/topics")
        self.assertEqual(response.status_code, 200)
        return response.json()["topics"]

    def test_query_projects_only_fields_used_by_endpoint(self):
        self.add_question(["Racionalidade"], uuid4(), [True])

        self.get_topics()

        self.assertEqual(
            self.db.selected_column_sets,
            [{"is_correct", "topics", "material_id"}],
        )

    def test_cosmetic_aliases_group_and_material_ids_are_deduplicated(self):
        first_material = uuid4()
        second_material = uuid4()
        self.add_question(
            ["Custo-benefício", "Custo benefício"],
            first_material,
            [True],
        )
        self.add_question(["custo-benefício"], first_material, [False])
        self.add_question(["Custo benefício"], second_material, [True])

        topics = self.get_topics()
        self.assertEqual(len(topics), 1)
        item = topics[0]
        self.assertEqual(item["topic"], "Custo-benefício")
        self.assertEqual(item["total_answers"], 3)
        self.assertEqual(item["correct_answers"], 2)
        self.assertEqual(item["incorrect_answers"], 1)
        self.assertAlmostEqual(item["accuracy"], 200 / 3)
        self.assertEqual(
            item["material_ids"],
            sorted([str(first_material), str(second_material)]),
        )

    def test_alias_labels_are_canonical_and_original_topics_are_unchanged(self):
        material_id = uuid4()
        original_topics = [
            "Falácias",
            "falácias",
            "Racionalidade",
            "racionalidade",
            "Custos irrecuperáveis",
            "custos irrecuperáveis",
        ]
        question = Question(
            id=uuid4(),
            material_id=material_id,
            question_text="Pergunta de teste",
            options={"0": "A"},
            correct_answer=0,
            topics=original_topics.copy(),
            difficulty="easy",
        )
        answer = UserAnswer(
            id=uuid4(),
            user_id=self.user_id,
            question_id=question.id,
            selected_answer=0,
            is_correct=True,
        )
        self.db.rows.append((answer, question))

        topic_items = {item["topic"]: item for item in self.get_topics()}

        self.assertEqual(
            set(topic_items),
            {"Falácias", "Racionalidade", "Custos irrecuperáveis"},
        )
        for item in topic_items.values():
            self.assertEqual(item["total_answers"], 1)
            self.assertEqual(item["material_ids"], [str(material_id)])
        self.assertEqual(question.topics, original_topics)

    def test_protected_topics_remain_distinct(self):
        material_id = uuid4()
        protected_topics = [
            "Custo de oportunidade",
            "Custos de oportunidade",
            "Racionalidade",
            "Racionalidade e custo benefício",
            "Tipos de racionalidade",
            "Falácias",
            "Falácia: custos irrecuperáveis",
            "Falácia: média vs marginal",
            "Falácia: medir proporções vs valores absolutos",
            "Falácias (custos irrecuperáveis)",
            "Custo-benefício",
            "Análise custo-benefício",
        ]
        self.add_question(protected_topics, material_id, [False])

        topic_items = {item["topic"]: item for item in self.get_topics()}

        expected_labels = {
            "Custo de oportunidade",
            "Custos de oportunidade",
            "Racionalidade",
            "Racionalidade e custo benefício",
            "Tipos de racionalidade",
            "Falácias",
            "Falácia: custos irrecuperáveis",
            "Falácia: média vs marginal",
            "Falácia: medir proporções vs valores absolutos",
            "Falácias (custos irrecuperáveis)",
            "Custo-benefício",
            "Análise custo-benefício",
        }

        self.assertEqual(set(topic_items), expected_labels)
        self.assertEqual(len(topic_items), len(protected_topics))
        self.assertTrue(
            all(item["total_answers"] == 1 for item in topic_items.values())
        )


if __name__ == "__main__":
    unittest.main()