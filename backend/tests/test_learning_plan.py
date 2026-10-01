import unittest
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.models.entities import Question, UserAnswer
from backend.routers.learning_plan import get_db, router


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class FakeSession:
    def __init__(self, rows=()):
        self.rows = list(rows)
        self.user_id = None
        self.statements = []
        self.result_rows = []

    def execute(self, statement):
        self.statements.append(statement)
        selected_columns = set(statement.selected_columns.keys())
        if selected_columns == {
            "question_id",
            "topics",
            "material_id",
            "total_answers",
            "correct_answers",
        }:
            questions = {}
            answers_by_question = {}
            for question, answer in self.rows:
                questions[question.id] = question
                if answer is not None and answer.user_id == self.user_id:
                    answers_by_question.setdefault(question.id, []).append(answer)

            self.result_rows = [
                (
                    question.id,
                    question.topics,
                    question.material_id,
                    len(answers_by_question.get(question.id, [])),
                    sum(
                        answer.is_correct
                        for answer in answers_by_question.get(question.id, [])
                    ),
                )
                for question in questions.values()
            ]
        else:
            questions = {}
            answers_by_question = {}
            for question, answer in self.rows:
                questions[question.id] = question
                if answer is not None and answer.user_id == self.user_id:
                    answers_by_question.setdefault(question.id, []).append(answer)

            self.result_rows = [
                (question, answer)
                for question_id, question in questions.items()
                for answer in answers_by_question.get(question_id, [None])
            ]

        return FakeResult(self.result_rows)


class LearningPlanEndpointTests(unittest.TestCase):
    def setUp(self):
        self.db = FakeSession()
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(app)
        self.user_id = uuid4()
        self.db.user_id = self.user_id

    def tearDown(self):
        self.client.close()

    def add_question(self, topics, material_id=None, answers=()):
        question = Question(
            id=uuid4(),
            material_id=material_id,
            question_text="Pergunta de teste",
            options={"0": "A"},
            correct_answer=0,
            topics=topics,
            difficulty="easy",
        )

        if answers:
            for is_correct in answers:
                answer = UserAnswer(
                    id=uuid4(),
                    user_id=self.user_id,
                    question_id=question.id,
                    selected_answer=0,
                    is_correct=is_correct,
                )
                self.db.rows.append((question, answer))
        else:
            self.db.rows.append((question, None))

        return question

    def get_items(self):
        response = self.client.get(f"/learning-plan/{self.user_id}")
        self.assertEqual(response.status_code, 200)
        return response.json()["items"]

    def test_user_without_answers_gets_explore_items_from_catalog(self):
        material_id = uuid4()
        self.add_question(["Introdução"], material_id)

        payload = self.client.get(f"/learning-plan/{self.user_id}").json()

        self.assertEqual(payload["user_id"], str(self.user_id))
        self.assertEqual(payload["minimum_answers_for_scored_actions"], 3)
        self.assertEqual(len(payload["items"]), 1)
        item = payload["items"][0]
        self.assertEqual(item["action"], "explore")
        self.assertEqual(item["total_answers"], 0)
        self.assertIsNone(item["accuracy"])
        self.assertFalse(item["has_sufficient_data"])
        self.assertEqual(item["material_ids"], [str(material_id)])

    def test_query_aggregates_user_attempts_per_question(self):
        material_id = uuid4()
        question = self.add_question(
            ["Racionalidade", "racionalidade", "Tema", "Racionalidade"],
            material_id,
            [True, False],
        )
        other_user_answer = UserAnswer(
            id=uuid4(),
            user_id=uuid4(),
            question_id=question.id,
            selected_answer=0,
            is_correct=True,
        )
        self.db.rows.append((question, other_user_answer))
        self.add_question(["Sem histórico"], material_id)

        items = {item["topic"]: item for item in self.get_items()}

        statement = self.db.statements[-1]
        self.assertEqual(
            set(statement.selected_columns.keys()),
            {
                "question_id",
                "topics",
                "material_id",
                "total_answers",
                "correct_answers",
            },
        )
        self.assertEqual(len(self.db.result_rows), 2)
        self.assertEqual(len(statement._group_by_clauses), 3)
        self.assertIn("user_answers.user_id =", str(statement))
        self.assertEqual(items["Racionalidade"]["total_answers"], 2)
        self.assertEqual(items["Racionalidade"]["correct_answers"], 1)
        self.assertEqual(items["Tema"]["total_answers"], 2)
        self.assertEqual(items["Tema"]["correct_answers"], 1)
        self.assertEqual(items["Sem histórico"]["total_answers"], 0)
        self.assertEqual(items["Sem histórico"]["action"], "explore")

    def test_empty_catalog_returns_no_items(self):
        self.assertEqual(self.get_items(), [])

    def test_one_two_and_three_attempts_obey_sample_threshold(self):
        material_id = uuid4()
        self.add_question(["Um"], material_id, [True])
        self.add_question(["Dois"], material_id, [True, False])
        self.add_question(["Tres"], material_id, [False, False, False])

        items = {item["topic"]: item for item in self.get_items()}

        self.assertEqual(items["Um"]["action"], "explore")
        self.assertIsNone(items["Um"]["accuracy"])
        self.assertEqual(items["Um"]["total_answers"], 1)
        self.assertEqual(items["Dois"]["action"], "explore")
        self.assertIsNone(items["Dois"]["accuracy"])
        self.assertEqual(items["Dois"]["total_answers"], 2)
        self.assertEqual(items["Tres"]["action"], "reinforce")
        self.assertTrue(items["Tres"]["has_sufficient_data"])
        self.assertEqual(items["Tres"]["total_answers"], 3)

    def test_accuracy_threshold_boundaries(self):
        material_id = uuid4()
        self.add_question(["Abaixo de 50"], material_id, [False, False, True])
        self.add_question(["Exatamente 50"], material_id, [True, True, False, False])
        self.add_question(["Abaixo de 80"], material_id, [True, True, True, False])
        self.add_question(["Exatamente 80"], material_id, [True, True, True, True, False])

        items = {item["topic"]: item for item in self.get_items()}

        self.assertEqual(items["Abaixo de 50"]["action"], "reinforce")
        self.assertEqual(items["Abaixo de 50"]["accuracy"], 33.33)
        self.assertEqual(items["Exatamente 50"]["action"], "consolidate")
        self.assertEqual(items["Exatamente 50"]["accuracy"], 50.0)
        self.assertEqual(items["Abaixo de 80"]["action"], "consolidate")
        self.assertEqual(items["Abaixo de 80"]["accuracy"], 75.0)
        self.assertEqual(items["Exatamente 80"]["action"], "deepen")
        self.assertEqual(items["Exatamente 80"]["accuracy"], 80.0)

    def test_multiple_topics_count_once_per_distinct_topic(self):
        material_id = uuid4()
        question = self.add_question(
            ["Álgebra", "Geometria", "Álgebra"],
            material_id,
            [False],
        )

        items = {item["topic"]: item for item in self.get_items()}

        self.assertEqual(items["Álgebra"]["total_answers"], 1)
        self.assertEqual(items["Geometria"]["total_answers"], 1)
        self.assertEqual(items["Álgebra"]["material_ids"], [str(material_id)])
        self.assertEqual(items["Geometria"]["material_ids"], [str(material_id)])
        self.assertEqual(question.topics.count("Álgebra"), 2)

    def test_cosmetic_cost_benefit_aliases_group_once_per_question(self):
        first_material = uuid4()
        second_material = uuid4()
        self.add_question(
            ["Custo-benefício", "Custo benefício"],
            first_material,
            [True, False],
        )
        self.add_question(["Custo benefício"], second_material, [True])
        self.add_question(["Custo-benefício"], first_material)

        matching_items = [
            item
            for item in self.get_items()
            if item["topic"] == "Custo-benefício"
        ]

        self.assertEqual(len(matching_items), 1)
        item = matching_items[0]
        self.assertEqual(item["total_answers"], 3)
        self.assertEqual(item["correct_answers"], 2)
        self.assertEqual(item["incorrect_answers"], 1)
        self.assertEqual(item["accuracy"], 66.67)
        self.assertEqual(
            item["material_ids"],
            sorted([str(first_material), str(second_material)]),
        )
        self.assertTrue(item["requires_material_choice"])

    def test_rationality_aliases_group_but_related_topics_remain_separate(self):
        material_id = uuid4()
        self.add_question(
            ["Racionalidade", "racionalidade"],
            material_id,
            [True, False, True],
        )
        self.add_question(
            ["Racionalidade e custo benefício"],
            material_id,
            [False],
        )
        self.add_question(["Tipos de racionalidade"], material_id)

        items = {item["topic"]: item for item in self.get_items()}

        self.assertIn("Racionalidade", items)
        self.assertEqual(items["Racionalidade"]["total_answers"], 3)
        self.assertIn("Racionalidade e custo benefício", items)
        self.assertIn("Tipos de racionalidade", items)
        self.assertEqual(len(items), 3)

    def test_fallacy_category_and_subcategories_remain_separate(self):
        material_id = uuid4()
        self.add_question(["Falácias", "falácias"], material_id, [False] * 3)
        subcategories = [
            "Falácia: custos irrecuperáveis",
            "Falácia: média vs marginal",
            "Falácia: medir proporções vs valores absolutos",
            "Falácias (custos irrecuperáveis)",
        ]
        for topic in subcategories:
            self.add_question([topic], material_id)

        items = {item["topic"]: item for item in self.get_items()}

        self.assertEqual(len(items), 1 + len(subcategories))
        self.assertEqual(items["Falácias"]["total_answers"], 3)
        for topic in subcategories:
            with self.subTest(topic=topic):
                self.assertIn(topic, items)
                self.assertEqual(items[topic]["total_answers"], 0)

    def test_material_ids_are_catalog_based_deduplicated_and_nullable(self):
        first_material = uuid4()
        second_material = uuid4()
        self.add_question(["Comum"], first_material)
        self.add_question(["Comum"], first_material)
        self.add_question(["Comum"], second_material)
        self.add_question(["Comum"], None)
        self.add_question(["Sem material"], None)

        items = {item["topic"]: item for item in self.get_items()}

        self.assertEqual(
            items["Comum"]["material_ids"],
            sorted([str(first_material), str(second_material)]),
        )
        self.assertTrue(items["Comum"]["requires_material_choice"])
        self.assertNotIn("Sem material", items)

    def test_single_material_does_not_require_choice(self):
        material_id = uuid4()
        self.add_question(["Único"], material_id)

        item = self.get_items()[0]

        self.assertEqual(item["material_ids"], [str(material_id)])
        self.assertFalse(item["requires_material_choice"])

    def test_order_and_priority_are_deterministic(self):
        material_id = uuid4()
        self.add_question(["B reforçar"], material_id, [False, True, False])
        self.add_question(["A reforçar"], material_id, [False, False, False])
        self.add_question(["B consolidar"], material_id, [True, True, True, False])
        self.add_question(["A consolidar"], material_id, [True, True, False, False])
        self.add_question(["A deepen"], material_id, [True, True, True, True, False])
        self.add_question(["B explore"], material_id, [False])
        self.add_question(["A explore"], material_id)

        items = self.get_items()
        expected_order = [
            "A reforçar",
            "B reforçar",
            "A consolidar",
            "B consolidar",
            "A deepen",
            "A explore",
            "B explore",
        ]

        self.assertEqual([item["topic"] for item in items], expected_order)
        self.assertEqual(
            [item["priority"] for item in items],
            list(range(1, len(items) + 1)),
        )

    def test_invalid_user_id_is_rejected_as_uuid(self):
        response = self.client.get("/learning-plan/not-a-uuid")

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()