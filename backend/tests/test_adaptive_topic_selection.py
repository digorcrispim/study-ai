import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import urlencode
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.models.entities import Question, UserAnswer
from backend.routers.answers import prepare_adaptive_questions
from backend.routers.questions import get_db as get_questions_db
from backend.routers.questions import router as questions_router


class FakeScalarResult:
    def __init__(self, values):
        self.values = values

    def all(self):
        return self.values

    def __iter__(self):
        return iter(self.values)

class FakeQueueSession:
    def __init__(self, questions, material_id, material_answers=(), history_rows=()):
        self.questions = questions
        self.material_id = material_id
        self.material_answers = list(material_answers)
        self.history_rows = list(history_rows)
        self.executed_column_sets = []

    def execute(self, statement):
        selected_keys = set(statement.selected_columns.keys())
        self.executed_column_sets.append(selected_keys)

        if selected_keys == {
            "question_id",
            "topics",
            "difficulty",
            "created_at",
        }:
            candidates = sorted(
                [
                    question
                    for question in self.questions
                    if question.material_id == self.material_id
                ],
                key=lambda question: question.created_at,
                reverse=True,
            )
            return FakeScalarResult(
                [
                    type(
                        "Candidate",
                        (),
                        {
                            "question_id": question.id,
                            "topics": question.topics,
                            "difficulty": question.difficulty,
                            "created_at": question.created_at,
                        },
                    )()
                    for question in candidates
                ]
            )

        if selected_keys == {
            "question_id",
            "is_correct",
            "answered_at",
            "topics",
        }:
            latest_by_question = {}
            for answer, question in sorted(
                self.history_rows,
                key=lambda row: row[0].answered_at,
                reverse=True,
            ):
                if answer.question_id not in latest_by_question:
                    latest_by_question[answer.question_id] = type(
                        "LatestAnswer",
                        (),
                        {
                            "question_id": answer.question_id,
                            "is_correct": answer.is_correct,
                            "answered_at": answer.answered_at,
                            "topics": question.topics,
                        },
                    )()
            return FakeScalarResult(list(latest_by_question.values()))

        if selected_keys == {
            "id",
            "material_id",
            "question_text",
            "options",
            "topics",
            "difficulty",
            "explanation",
        }:
            return FakeScalarResult(
                [
                    type(
                        "QuestionResponseRow",
                        (),
                        {
                            "id": question.id,
                            "material_id": question.material_id,
                            "question_text": question.question_text,
                            "options": question.options,
                            "topics": question.topics,
                            "difficulty": question.difficulty,
                            "explanation": question.explanation,
                        },
                    )()
                    for question in self.questions
                    if question.material_id == self.material_id
                ]
            )

        if {"selected_answer", "is_correct", "answered_at", "question_text"}.issubset(
            selected_keys
        ):
            return FakeScalarResult(
                sorted(
                    self.history_rows,
                    key=lambda row: row[0].answered_at,
                    reverse=True,
                )
            )

        raise AssertionError(f"Unexpected selected columns: {selected_keys}")


class FakeReuseSession:
    def __init__(self, questions, material_id, difficulty):
        self.questions = questions
        self.material_id = material_id
        self.difficulty = difficulty

    def scalars(self, statement):
        return FakeScalarResult(
            [
                question
                for question in self.questions
                if question.material_id == self.material_id
                and question.difficulty == self.difficulty
            ]
        )

    def get(self, model, entity_id):
        raise AssertionError("Material lookup should not be needed for reuse")


class AdaptiveTopicSelectionTests(unittest.TestCase):
    def setUp(self):
        self.material_id = uuid4()
        self.user_id = uuid4()
        self.questions = []
        self.db = FakeQueueSession(self.questions, self.material_id)
        app = FastAPI()
        app.include_router(questions_router)
        app.dependency_overrides[get_questions_db] = lambda: self.db
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()

    def make_question(
        self,
        topics,
        material_id=None,
        difficulty="medium",
        created_at=None,
    ):
        return Question(
            id=uuid4(),
            material_id=material_id or self.material_id,
            question_text="Pergunta de teste",
            options={"0": "A", "1": "B", "2": "C", "3": "D"},
            correct_answer=0,
            explanation=None,
            topics=topics.copy(),
            difficulty=difficulty,
            created_at=created_at or datetime.now(timezone.utc),
        )

    def make_answer(self, question, is_correct, answered_at):
        return UserAnswer(
            id=uuid4(),
            user_id=self.user_id,
            question_id=question.id,
            selected_answer=0,
            is_correct=is_correct,
            answered_at=answered_at,
        )

    def request_queue(self, topic=None, limit=None):
        self.db.executed_column_sets = []
        query_params = {}
        if topic is not None:
            query_params["topic"] = topic
        if limit is not None:
            query_params["limit"] = limit
        query = urlencode(query_params)
        query_string = f"?{query}" if query else ""
        response = self.client.get(
            f"/questions/material/{self.material_id}/adaptive/{self.user_id}{query_string}"
        )
        self.assertEqual(response.status_code, 200)
        return response.json()

    def set_queue_data(self, questions, material_answers=(), history_rows=()):
        self.questions[:] = questions
        self.db = FakeQueueSession(
            self.questions,
            self.material_id,
            material_answers,
            history_rows,
        )

    def test_all_approved_aliases_select_questions_and_preserve_raw_topics(self):
        alias_pairs = [
            ("Custo-benefício", "Custo benefício"),
            ("Custo benefício", "custo-benefício"),
            ("racionalidade", "Racionalidade"),
            ("Falácias", "falácias"),
            ("Custos irrecuperáveis", "custos irrecuperáveis"),
        ]

        for requested_topic, stored_topic in alias_pairs:
            with self.subTest(requested=requested_topic, stored=stored_topic):
                question = self.make_question([stored_topic])
                self.set_queue_data([question])

                response_questions = self.request_queue(requested_topic)

                self.assertEqual(
                    [item["id"] for item in response_questions],
                    [str(question.id)],
                )
                self.assertEqual(response_questions[0]["topics"], [stored_topic])
                self.assertEqual(question.topics, [stored_topic])

    def test_protected_topics_and_partial_matches_are_excluded(self):
        questions = [
            self.make_question(["Custo de oportunidade"]),
            self.make_question(["Custos de oportunidade"]),
            self.make_question(["Racionalidade"]),
            self.make_question(["racionalidade"]),
            self.make_question(["Racionalidade e custo benefício"]),
            self.make_question(["Tipos de racionalidade"]),
            self.make_question(["Falácias"]),
            self.make_question(["falácias"]),
            self.make_question(["Falácia: custos irrecuperáveis"]),
            self.make_question(["Falácia: média vs marginal"]),
            self.make_question(
                ["Falácia: medir proporções vs valores absolutos"]
            ),
            self.make_question(["Falácias (custos irrecuperáveis)"]),
            self.make_question(
                ["Falácias (proporções; média vs marginal)"]
            ),
            self.make_question(["Custo-benefício"]),
            self.make_question(["Custo benefício"]),
            self.make_question(["custo-benefício"]),
            self.make_question(["Análise custo-benefício"]),
            self.make_question(["Custo-benefício ampliado"]),
        ]
        self.set_queue_data(questions)

        self.assertEqual(
            [item["topics"] for item in self.request_queue("Custo de oportunidade")],
            [["Custo de oportunidade"]],
        )
        self.assertEqual(
            [item["topics"] for item in self.request_queue("Custos de oportunidade")],
            [["Custos de oportunidade"]],
        )
        self.assertEqual(
            {item["topics"][0] for item in self.request_queue("Racionalidade")},
            {"Racionalidade", "racionalidade"},
        )
        self.assertEqual(
            {item["topics"][0] for item in self.request_queue("Falácias")},
            {"Falácias", "falácias"},
        )
        self.assertEqual(
            {item["topics"][0] for item in self.request_queue("Custo-benefício")},
            {"Custo-benefício", "Custo benefício", "custo-benefício"},
        )

    def test_material_filter_is_preserved(self):
        matching_question = self.make_question(["Custo benefício"])
        other_material_question = self.make_question(
            ["Custo-benefício"],
            material_id=uuid4(),
        )
        self.set_queue_data([matching_question, other_material_question])

        response_questions = self.request_queue("Custo-benefício")

        self.assertEqual(len(response_questions), 1)
        self.assertEqual(response_questions[0]["id"], str(matching_question.id))

    def test_priority_groups_and_stable_inner_order_are_preserved(self):
        now = datetime.now(timezone.utc)
        questions = [
            self.make_question(
                ["Equilíbrio"],
                created_at=now - timedelta(minutes=6 - index),
            )
            for index in range(6)
        ]
        answer_time = now - timedelta(hours=1)
        material_answers = [
            self.make_answer(questions[0], False, answer_time),
            self.make_answer(questions[1], False, answer_time),
            self.make_answer(questions[4], True, answer_time),
            self.make_answer(questions[5], True, answer_time),
        ]
        history_rows = [
            (answer, question)
            for answer, question in zip(
                material_answers,
                [questions[0], questions[1], questions[4], questions[5]],
            )
        ]
        self.set_queue_data(questions, material_answers, history_rows)

        result = self.request_queue("Equilíbrio")

        # Candidates initially come in created_at DESC order. Within equal
        # sort keys, Python's stable sort preserves that order in each group.
        expected_ids = [
            questions[1].id,
            questions[0].id,
            questions[3].id,
            questions[2].id,
            questions[5].id,
            questions[4].id,
        ]
        self.assertEqual([item["id"] for item in result], list(map(str, expected_ids)))

    def test_existing_priority_tuple_is_preserved_within_groups(self):
        now = datetime.now(timezone.utc)
        questions = [
            self.make_question(["Low accuracy"], difficulty="easy"),
            self.make_question(["High accuracy"], difficulty="medium"),
            self.make_question(["Far difficulty"], difficulty="easy"),
            self.make_question(["Near difficulty"], difficulty="medium"),
            self.make_question(
                ["Recent tie"],
                difficulty="easy",
                created_at=now,
            ),
            self.make_question(
                ["Recent tie"],
                difficulty="easy",
                created_at=now - timedelta(minutes=1),
            ),
        ]

        material_answers = [
            self.make_answer(questions[0], False, now),
            self.make_answer(questions[1], False, now),
            self.make_answer(questions[2], False, now),
            self.make_answer(questions[3], False, now),
            self.make_answer(questions[4], False, now - timedelta(minutes=1)),
            self.make_answer(questions[5], False, now),
        ]

        history_rows = [
            (answer, question)
            for answer, question in zip(material_answers, questions)
        ]

        # Low accuracy is 0%; High accuracy is 75%. Both candidates have
        # zero difficulty distance so accuracy must decide first.
        helper_questions = [
            self.make_question(["High accuracy"], material_id=uuid4())
            for _ in range(3)
        ]
        helper_answers = [
            self.make_answer(question, True, now)
            for question in helper_questions
        ]
        history_rows.extend(zip(helper_answers, helper_questions))

        # Both difficulty candidates have 60% topic accuracy. Medium is the
        # target rank, so it wins on the second sort-key component.
        far_helpers = [
            self.make_question(["Far difficulty"], material_id=uuid4())
            for _ in range(4)
        ]
        far_answers = [
            self.make_answer(question, is_correct, now)
            for question, is_correct in zip(
                far_helpers,
                [False, True, True, True],
            )
        ]
        near_helpers = [
            self.make_question(["Near difficulty"], material_id=uuid4())
            for _ in range(4)
        ]
        near_answers = [
            self.make_answer(question, is_correct, now)
            for question, is_correct in zip(
                near_helpers,
                [False, True, True, True],
            )
        ]
        history_rows.extend(zip(far_answers, far_helpers))
        history_rows.extend(zip(near_answers, near_helpers))

        # Equal topic accuracy and difficulty: latest answered_at decides,
        # even though created_at initially places the older answer first.
        self.set_queue_data(
            questions,
            material_answers,
            history_rows,
        )

        result = self.request_queue()
        result_ids = [item["id"] for item in result]
        self.assertLess(
            result_ids.index(str(questions[0].id)),
            result_ids.index(str(questions[1].id)),
        )
        self.assertLess(
            result_ids.index(str(questions[3].id)),
            result_ids.index(str(questions[2].id)),
        )
        self.assertLess(
            result_ids.index(str(questions[5].id)),
            result_ids.index(str(questions[4].id)),
        )

    def test_only_latest_answer_sets_each_questions_state(self):
        now = datetime.now(timezone.utc)
        question_wrong = self.make_question(["Atualização"])
        question_changed = self.make_question(["Atualização"])
        older_answer = self.make_answer(
            question_changed,
            False,
            now - timedelta(days=1),
        )
        latest_answer = self.make_answer(question_changed, True, now)
        wrong_answer = self.make_answer(question_wrong, False, now)
        self.set_queue_data(
            [question_wrong, question_changed],
            [older_answer, latest_answer, wrong_answer],
            [
                (older_answer, question_changed),
                (latest_answer, question_changed),
                (wrong_answer, question_wrong),
            ],
        )

        result = self.request_queue("Atualização")

        self.assertEqual(
            [item["id"] for item in result],
            [str(question_wrong.id), str(question_changed.id)],
        )

    def test_without_limit_returns_full_order_and_limit_returns_exact_prefix(self):
        now = datetime.now(timezone.utc)
        questions = [
            self.make_question(
                ["Fila"],
                created_at=now - timedelta(minutes=index),
            )
            for index in range(7)
        ]
        material_answers = [
            self.make_answer(question, False, now - timedelta(minutes=index))
            for index, question in enumerate(questions[:2])
        ]
        self.set_queue_data(
            questions,
            material_answers,
            list(zip(material_answers, questions)),
        )

        complete_result = self.request_queue("Fila")
        limited_result = self.request_queue("Fila", limit=5)

        self.assertEqual(len(complete_result), 7)
        self.assertEqual(len(limited_result), 5)
        self.assertEqual(
            [item["id"] for item in limited_result],
            [item["id"] for item in complete_result[:5]],
        )

    def test_nonpositive_limit_is_rejected(self):
        response = self.client.get(
            f"/questions/material/{self.material_id}/adaptive/{self.user_id}?limit=0"
        )

        self.assertEqual(response.status_code, 422)

    def test_existing_questions_are_reused_by_canonical_topic(self):
        question = self.make_question(["Custo-benefício"], difficulty="medium")
        candidates = [
            self.make_question(["Custo benefício"], difficulty="easy")
        ]
        candidates.extend(
            self.make_question(["custo-benefício"], difficulty="easy")
            for _ in range(2)
        )
        protected_candidate = self.make_question(
            ["Análise custo-benefício"],
            difficulty="easy",
        )
        candidates.append(protected_candidate)
        db = FakeReuseSession(candidates, self.material_id, "easy")

        with patch(
            "backend.routers.answers.generate_adaptive_questions"
        ) as generate_questions:
            reused_questions = prepare_adaptive_questions(
                question=question,
                user_id=self.user_id,
                is_correct=False,
                db=db,
                topic="Custo benefício",
            )

        self.assertEqual(len(reused_questions), 3)
        self.assertNotIn(protected_candidate, reused_questions)
        self.assertEqual(
            [candidate.topics for candidate in reused_questions],
            [["Custo benefício"], ["custo-benefício"], ["custo-benefício"]],
        )
        generate_questions.assert_not_called()
        self.assertEqual(question.topics, ["Custo-benefício"])


if __name__ == "__main__":
    unittest.main()